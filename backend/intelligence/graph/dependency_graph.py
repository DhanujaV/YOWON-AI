"""
dependency_graph.py — AST and manifest-driven dependency graph.

Constructs dependency representation from SemanticIndex, supporting Python,
Node.js, Go, Rust, Java, C#, and Docker.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder
from intelligence.semantic_index import SemanticIndex


class DependencyGraphBuilder(BaseGraphBuilder):
    """
    Constructs multi-language dependency graph.
    Lists package ecosystem dependencies derived from SemanticIndex.
    """

    def build(self, semantic_index: Any, project_name: str) -> None:
        self.nodes = []
        self.edges = []

        # 1. Main project node
        root_id = "project"
        self.nodes.append(GraphNode(
            id=root_id,
            label=project_name,
            type="project",
            metadata={"description": "Target codebase"}
        ))

        # Check if argument is SemanticIndex or fallback to plain dict
        if isinstance(semantic_index, SemanticIndex):
            idx = semantic_index
        else:
            # Fallback for compatibility
            idx = SemanticIndex()
            if isinstance(semantic_index, dict):
                idx.python_deps.update({str(k): str(v) for k, v in semantic_index.items()})
            elif isinstance(semantic_index, list):
                for item in semantic_index:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("package", "")
                        version = item.get("version", "")
                        if name:
                            idx.python_deps[str(name)] = str(version)
                    elif isinstance(item, str):
                        idx.python_deps[item] = ""

        # Map dependencies categorized by ecosystem
        ecosystems = [
            (idx.python_deps, "Python"),
            (idx.node_deps,   "Node.js"),
            (idx.go_deps,     "Go"),
            (idx.rust_deps,    "Rust"),
            (idx.java_deps,    "Java"),
            (idx.csharp_deps,  "C#"),
        ]

        for deps, lang in ecosystems:
            if not deps:
                continue

            # Create an intermediate ecosystem node to group them nicely if needed
            eco_id = f"eco_{lang.lower().replace('.', '_').replace('#', 'sharp')}"
            self.nodes.append(GraphNode(
                id=eco_id,
                label=f"{lang} Packages",
                type="ecosystem",
                metadata={"language": lang}
            ))
            self.edges.append(GraphEdge(
                source=root_id,
                target=eco_id,
                label="uses"
            ))

            for dep_name, version in deps.items():
                dep_id = f"dep_{lang.lower()}_{dep_name.lower().replace('-', '_').replace('.', '_')}"
                self.nodes.append(GraphNode(
                    id=dep_id,
                    label=f"{dep_name}@{version}" if version else dep_name,
                    type="dependency",
                    metadata={"version": version, "ecosystem": lang}
                ))
                # Link ecosystem node to the dependency
                self.edges.append(GraphEdge(
                    source=eco_id,
                    target=dep_id,
                    label="requires"
                ))

        # Support Docker images/services if any
        if idx.docker_images:
            eco_id = "eco_docker"
            if not any(n.id == eco_id for n in self.nodes):
                self.nodes.append(GraphNode(
                    id=eco_id,
                    label="Containers",
                    type="ecosystem",
                    metadata={"language": "Docker"}
                ))
                self.edges.append(GraphEdge(
                    source=root_id,
                    target=eco_id,
                    label="deploys"
                ))

            for img in idx.docker_images:
                dep_id = f"dep_docker_{img.lower().replace(':', '_').replace('/', '_').replace('.', '_')}"
                self.nodes.append(GraphNode(
                    id=dep_id,
                    label=img,
                    type="container",
                    metadata={"image": img}
                ))
                self.edges.append(GraphEdge(
                    source=eco_id,
                    target=dep_id,
                    label="runs"
                ))

        # Add explicit framework dependency relationships if found
        node_ids = {n.id for n in self.nodes}
        for n in self.nodes:
            if n.type == "dependency":
                label_lower = n.label.lower()
                # e.g., CrewAI requires OpenAI or LangChain
                if "crewai" in label_lower:
                    for target in ("openai", "langchain"):
                        target_id = next((node.id for node in self.nodes
                                          if node.type == "dependency" and target in node.label.lower()), None)
                        if target_id and target_id in node_ids:
                            self.edges.append(GraphEdge(
                                source=n.id,
                                target=target_id,
                                label="orchestrates"
                            ))
                elif "fastapi" in label_lower:
                    for target in ("sqlalchemy", "pydantic"):
                        target_id = next((node.id for node in self.nodes
                                          if node.type == "dependency" and target in node.label.lower()), None)
                        if target_id and target_id in node_ids:
                            self.edges.append(GraphEdge(
                                source=n.id,
                                target=target_id,
                                label="uses"
                            ))
