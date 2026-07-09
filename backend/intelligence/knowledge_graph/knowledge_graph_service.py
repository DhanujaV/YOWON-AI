import json
from collections import deque
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from database import KnowledgeGraphNode, KnowledgeGraphEdge

import logging
import hashlib

logger = logging.getLogger(__name__)

def get_deterministic_id(snapshot_id: str, commit_sha: str, raw_id: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(commit_sha.encode("utf-8"))
    hasher.update(snapshot_id.encode("utf-8"))
    hasher.update(raw_id.encode("utf-8"))
    return hasher.hexdigest()

def sync_knowledge_graph(
    db: Session,
    snapshot_id: str,
    commit_sha: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]]
) -> bool:
    """Deletes existing knowledge graph nodes/edges for snapshot, then merges new ones (upsert)."""
    try:
        # Delete old edges
        db.query(KnowledgeGraphEdge).filter(
            KnowledgeGraphEdge.repository_snapshot_id == snapshot_id
        ).delete(synchronize_session=False)

        # Delete old nodes
        db.query(KnowledgeGraphNode).filter(
            KnowledgeGraphNode.repository_snapshot_id == snapshot_id
        ).delete(synchronize_session=False)

        db.commit()

        # Save new nodes using merge() for idempotency
        for n in nodes:
            metadata = dict(n.get("metadata") or {})
            metadata["original_id"] = n["id"]  # Store original ID in metadata for de-hashing

            hashed_id = get_deterministic_id(snapshot_id, commit_sha, n["id"])
            node_obj = KnowledgeGraphNode(
                node_id=hashed_id,
                repository_snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                label=n["label"],
                type=n["type"],
                metadata_json=json.dumps(metadata)
            )
            db.merge(node_obj)

        # Save new edges using merge()
        for e in edges:
            hashed_source = get_deterministic_id(snapshot_id, commit_sha, e["source"])
            hashed_target = get_deterministic_id(snapshot_id, commit_sha, e["target"])
            edge_obj = KnowledgeGraphEdge(
                repository_snapshot_id=snapshot_id,
                commit_sha=commit_sha,
                source=hashed_source,
                target=hashed_target,
                relation=e["relation"]
            )
            db.merge(edge_obj)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.exception(f"[Intel] Failed to sync knowledge graph for snapshot {snapshot_id}: {e}")
        return False

def get_knowledge_graph_data(db: Session, snapshot_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves all nodes and edges for the snapshot and restores original human-readable IDs."""
    db_nodes = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.repository_snapshot_id == snapshot_id
    ).all()

    db_edges = db.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.repository_snapshot_id == snapshot_id
    ).all()

    hash_to_original: Dict[str, str] = {}
    nodes = []
    for n in db_nodes:
        metadata = {}
        if n.metadata_json:
            try:
                metadata = json.loads(n.metadata_json)
            except Exception:
                pass
        original_id = metadata.get("original_id", n.node_id)
        hash_to_original[n.node_id] = original_id

        nodes.append({
            "id": original_id,
            "label": n.label,
            "type": n.type,
            "metadata": metadata
        })

    edges = []
    for e in db_edges:
        edges.append({
            "source": hash_to_original.get(e.source, e.source),
            "target": hash_to_original.get(e.target, e.target),
            "relation": e.relation
        })

    return {"nodes": nodes, "edges": edges}


def find_shortest_dependency_path(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    source: str,
    target: str
) -> Dict[str, Any]:
    """BFS shortest path pathfinder for dependency tracing between nodes."""
    node_ids = {n["id"] for n in nodes}
    if source not in node_ids or target not in node_ids:
        return {"nodes": [], "edges": []}

    # Build adjacency list (directed or undirected? Let's check directed first)
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    edge_map: Dict[tuple, Dict[str, Any]] = {}
    
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        if src in adj and tgt in adj:
            adj[src].append(tgt)
            edge_map[(src, tgt)] = e

    # BFS traversal
    queue = deque([[source]])
    visited = {source}
    
    found_path: Optional[List[str]] = None
    while queue:
        path = queue.popleft()
        current = path[-1]
        
        if current == target:
            found_path = path
            break
            
        for neighbor in adj[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)

    if not found_path:
        return {"nodes": [], "edges": []}

    # Extract nodes and edges in the path
    path_nodes = [n for n in nodes if n["id"] in found_path]
    path_edges = []
    for i in range(len(found_path) - 1):
        edge = edge_map.get((found_path[i], found_path[i+1]))
        if edge:
            path_edges.append(edge)

    return {"nodes": path_nodes, "edges": path_edges}

def collapse_folder_nodes(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Collapses file nodes inside folders to parent directories for uncluttered visual layouts."""
    collapsed_nodes: List[Dict[str, Any]] = []
    collapsed_edges: List[Dict[str, Any]] = []
    
    folder_nodes: Dict[str, Dict[str, Any]] = {}
    file_to_folder: Dict[str, str] = {}
    
    # 1. Separate folders and files
    for n in nodes:
        if n["type"] == "file" and "/" in n["id"]:
            fpath = n["id"]
            folder_path = fpath.rsplit("/", 1)[0]
            file_to_folder[fpath] = folder_path
            
            if folder_path not in folder_nodes:
                folder_nodes[folder_path] = {
                    "id": folder_path,
                    "label": folder_path,
                    "type": "folder",
                    "metadata": {"collapsed": True}
                }
        else:
            collapsed_nodes.append(n)

    # Add folder nodes
    for fnode in folder_nodes.values():
        collapsed_nodes.append(fnode)

    # 2. Redirect edges
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        
        new_src = file_to_folder.get(src, src)
        new_tgt = file_to_folder.get(tgt, tgt)
        
        if new_src != new_tgt:
            # Check if this edge already exists in collapsed list
            edge_exists = any(
                ce["source"] == new_src and ce["target"] == new_tgt and ce["relation"] == e["relation"]
                for ce in collapsed_edges
            )
            if not edge_exists:
                collapsed_edges.append({
                    "source": new_src,
                    "target": new_tgt,
                    "relation": e["relation"]
                })

    return {"nodes": collapsed_nodes, "edges": collapsed_edges}
