import time
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database import RepositorySnapshot, Evidence, Recommendation, RepositoryFile

from intelligence.models import (
    RepositoryTreeNode, SymbolRecord, EvidenceRecord, 
    TechnologyRecord, RecommendationRecord
)
from intelligence.cache_engine import RepositoryAnalysisCache
from intelligence.symbol_indexer import SymbolIndexer
from intelligence.security_engine import SecurityEngine
from intelligence.evidence_engine import EvidenceEngine
from intelligence.architecture_engine import ArchitectureEngine
from intelligence.metrics_engine import MetricsEngine
from intelligence.health_engine import HealthEngine
from intelligence.recommendation_engine import RecommendationEngine

from intelligence.graph.architecture_graph import ArchitectureGraphBuilder
from intelligence.graph.dependency_graph import DependencyGraphBuilder
from intelligence.graph.call_graph import CallGraphBuilder
from intelligence.graph.technology_graph import TechnologyGraphBuilder

logger = logging.getLogger(__name__)

def run_repository_intelligence(db: Session, evaluation: Any, snapshot_id: str) -> Dict[str, Any]:
    """Orchestrates code intelligence static analysis over a repository snapshot."""
    t_start = time.perf_counter()
    
    # 1. Fetch current snapshot and commit details
    snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == snapshot_id).first()
    if not snapshot:
        raise ValueError(f"Snapshot not found: {snapshot_id}")
    
    commit_sha = snapshot.commit_sha
    
    # 2. Check Hybrid Cache
    cached_data = RepositoryAnalysisCache.get(commit_sha, db)
    if cached_data:
        logger.info("[Intel] Cache hit for commit=%s", commit_sha)
        # Populate DB tables if they are empty
        _sync_database_records(db, evaluation, cached_data["evidence"], cached_data["recommendations"])
        return cached_data

    logger.info("[Intel] Cache miss. Initiating static analysis for commit=%s", commit_sha)

    # 3. Read cached repository tree metadata or query DB files
    # Let's read folder_structure from snapshot
    files_list = []
    if snapshot.folder_structure:
        try:
            files_list = json.loads(snapshot.folder_structure)
        except Exception:
            files_list = []

    # Get manifest dependencies
    dependencies = {}
    if snapshot.dependency_summary:
        try:
            dependencies = json.loads(snapshot.dependency_summary)
        except Exception:
            dependencies = {}

    # Initialize engines
    symbol_indexer = SymbolIndexer()
    security_engine = SecurityEngine()
    
    # Check if there is a previous snapshot for incremental analysis
    prev_snapshot_id = snapshot.previous_snapshot_id
    prev_snapshot = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == prev_snapshot_id).first() if prev_snapshot_id else None
    
    # Read files contents from repository cache if available
    # We will query RepositoryFile or load from cache
    # In YOWON AI, high-signal file contents are stored in main.py parsed cache,
    # or we can read them from REPOSITORY_CACHE_DIR/{digest}.json source_files!
    source_files_content = _load_source_contents_from_github_cache(snapshot.repository.github_url)

    # 4. Symbol indexing & Security scanning (Incremental if previous analysis exists)
    t_index = time.perf_counter()
    for fpath in files_list:
        content = source_files_content.get(fpath, "")
        symbol_indexer.index_file(fpath, content)
        security_engine.scan_file(fpath, content)

    # Compile files imports mapping
    file_imports = {}
    for fpath in files_list:
        parser = symbol_indexer.by_file.get(fpath)
        file_imports[fpath] = symbol_indexer.by_file[fpath][0].relationships if symbol_indexer.by_file.get(fpath) else [] # Wait, parser.get_imports() is safer
        # Let's run parser get_imports
        from intelligence.parsers.parser_registry import ParserRegistry
        parser = ParserRegistry.get_parser(fpath)
        parser.load(source_files_content.get(fpath, ""), fpath)
        if parser.parse():
            file_imports[fpath] = parser.get_imports()
        else:
            file_imports[fpath] = []

    # 5. Run Evidence Engine
    evidence_engine = EvidenceEngine()
    symbols = symbol_indexer.get_all_symbols()
    security_findings = security_engine.get_all_findings()
    
    evidence_records = evidence_engine.analyze_repository(
        symbols=symbols,
        dependencies=dependencies,
        security_findings=security_findings,
        file_imports=file_imports
    )

    # 6. Run Architecture Engine
    architecture_engine = ArchitectureEngine()
    layers = architecture_engine.analyze(evidence_records, files_list)

    # 7. Run Metrics Engine for each file
    file_metrics = {}
    for fpath in files_list:
        content = source_files_content.get(fpath, "")
        f_symbols = symbol_indexer.get_file_symbols(fpath)
        f_security = security_engine.get_findings_for_file(fpath)
        
        # Calculate incoming import reference count
        imports_count = sum(1 for target, imps in file_imports.items() if any(fpath in imp or fpath.split("/")[-1].split(".")[0] in imp for imp in imps))
        
        # Check test file mapping
        has_test = any(t in fpath.lower() for t in ("test_", "_test", "spec"))
        has_test_file = False
        if not has_test:
            basename = fpath.split("/")[-1].split(".")[0]
            has_test_file = any(basename in tf.lower() and tf != fpath for tf in files_list if any(t in tf.lower() for t in ("test_", "_test", "spec")))

        file_metrics[fpath] = MetricsEngine().calculate_file_metrics(
            file_path=fpath,
            content=content,
            symbols=f_symbols,
            imports_count=imports_count,
            security_findings=f_security,
            has_test_file=has_test_file
        )

    # 8. Run Health Engine
    health_engine = HealthEngine()
    health_scores = health_engine.calculate_health(
        files=files_list,
        dependencies=dependencies,
        security_findings=security_findings,
        file_metrics=file_metrics
    )

    # 9. Run Recommendation Engine
    recommendation_engine = RecommendationEngine()
    recommendation_records = recommendation_engine.generate_recommendations(evidence_records)

    # 10. Build Graphs
    arch_builder = ArchitectureGraphBuilder()
    arch_builder.build(layers)
    arch_graph = arch_builder.serialize()

    dep_builder = DependencyGraphBuilder()
    dep_builder.build(dependencies, snapshot.repository.name or "Project")
    dep_graph = dep_builder.serialize()

    call_builder = CallGraphBuilder()
    call_builder.build(file_imports, files_list)
    call_graph = call_builder.serialize()

    techs_list = list({t for l in layers.values() for t in l["techs"]})
    tech_builder = TechnologyGraphBuilder()
    tech_builder.build(techs_list)
    tech_graph = tech_builder.serialize()

    # 11. Compile Repository Tree representation
    repo_tree = _build_hierarchical_tree(files_list, file_metrics)

    # 12. Structure Cache Data Output
    analysis_output = {
        "repository_snapshot_id": snapshot_id,
        "repository_tree": repo_tree,
        "architecture_graph": arch_graph,
        "dependency_graph": dep_graph,
        "technology_graph": tech_graph,
        "call_graph": call_graph,
        "metrics": file_metrics,
        "health": health_scores,
        "evidence": [ev.model_dump() for ev in evidence_records],
        "recommendations": [rec.model_dump() for rec in recommendation_records]
    }

    # 13. Save to Hybrid Cache (Memory, DB, Disk)
    RepositoryAnalysisCache.set(commit_sha, snapshot_id, analysis_output, db)
    
    # 14. Save findings to DB tables for persistence and UI references
    _sync_database_records(
        db=db,
        evaluation=evaluation,
        evidence_list=analysis_output["evidence"],
        recommendation_list=analysis_output["recommendations"]
    )

    t_end = time.perf_counter()
    logger.info("[Intel] Static analysis completed in %.2f seconds for commit=%s", t_end - t_start, commit_sha)
    
    return analysis_output

def _build_hierarchical_tree(files: List[str], file_metrics: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Builds a nested folder tree JSON representation from flat path lists."""
    root = {"name": "root", "type": "dir", "children": {}}
    
    for fpath in files:
        parts = fpath.split("/")
        current = root
        for idx, part in enumerate(parts):
            if idx == len(parts) - 1:
                # File node
                metrics = file_metrics.get(fpath, {})
                current["children"][part] = {
                    "name": part,
                    "path": fpath,
                    "type": "file",
                    "language": fpath.split(".")[-1] if "." in fpath else "unknown",
                    "extension": "." + fpath.split(".")[-1] if "." in fpath else None,
                    "size": metrics.get("size_bytes", 0),
                    "loc": metrics.get("loc", 0),
                    "sha256": hashlib.sha256(fpath.encode()).hexdigest()[:16],
                    "roles": metrics.get("roles", {"Unknown": 1.0}),
                    "generated": "node_modules" in fpath or "build" in fpath or "dist" in fpath,
                    "ignored": False
                }
            else:
                # Directory node
                if part not in current["children"]:
                    current["children"][part] = {
                        "name": part,
                        "path": "/".join(parts[:idx+1]),
                        "type": "dir",
                        "children": {}
                    }
                current = current["children"][part]

    # Convert dictionaries to lists recursively
    def dict_to_list(node):
        if "children" in node:
            node["children"] = [dict_to_list(child) for child in node["children"].values()]
        return node

    tree_list = [dict_to_list(child) for child in root["children"].values()]
    return tree_list

def _load_source_contents_from_github_cache(github_url: str) -> Dict[str, str]:
    """Loads sampled file contents from github_tool cached json dictionary."""
    from tools.github_tool import _cache_path
    from tools.github_tool import _repo_name_from_url
    
    contents = {}
    try:
        repo_name = _repo_name_from_url(github_url)
        path = _cache_path(repo_name)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            data = payload.get("data", {})
            for item in data.get("source_files", []):
                contents[item["path"]] = item.get("content", "")
            for item in data.get("python_files", []):
                contents[item["path"]] = item.get("content", "")
            # Include dependencies text if available
            for dpath, dcontent in data.get("dependencies", {}).items():
                contents[dpath] = dcontent
    except Exception:
        pass
    return contents

def _sync_database_records(
    db: Session,
    evaluation: Any,
    evidence_list: List[Dict[str, Any]],
    recommendation_list: List[Dict[str, Any]]
) -> None:
    """Saves analyzed evidence and recommendations into the DB for compatibility."""
    try:
        # Clear existing evidence and recommendations linked to this evaluation
        db.query(Evidence).filter(Evidence.evaluation_id == evaluation.evaluation_id).delete()
        db.query(Recommendation).filter(Recommendation.evaluation_id == evaluation.evaluation_id).delete()
        db.commit()

        # Insert new Evidence records
        for ev in evidence_list[:100]: # Limit for performance
            db.add(Evidence(
                evaluation_id=evaluation.evaluation_id,
                category=ev["rule_id"].replace("RULE_", "").split("_")[0],
                finding=f"[{ev['rule_id']}] Detected in {ev['file_path']} at line {ev['line_start']}",
                file_path=ev["file_path"],
                line_start=ev["line_start"],
                line_end=ev["line_end"],
                confidence=ev["confidence"]
            ))

        # Insert new Recommendations
        for rec in recommendation_list[:25]:
            db.add(Recommendation(
                id=rec["id"],
                evaluation_id=evaluation.evaluation_id,
                rule_id=rec["triggered_rule_ids"][0] if rec["triggered_rule_ids"] else "GENERAL",
                title=rec["title"],
                recommendation=rec["recommendation"],
                severity=rec["severity"],
                confidence=rec["confidence"]
            ))
        db.commit()
    except Exception as e:
        logger.exception("[Intel] Failed to sync database records for evaluation=%s: %s", evaluation.evaluation_id, e)
        db.rollback()
