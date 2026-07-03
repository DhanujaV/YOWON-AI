from typing import Dict, Any, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder

class DependencyGraphBuilder(BaseGraphBuilder):
    def build(self, dependencies: Dict[str, str], project_name: str) -> None:
        """Constructs Dependency Graph listing package ecosystem dependencies."""
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

        # 2. Package nodes
        for dep_name, version in dependencies.items():
            dep_id = f"dep_{dep_name.lower().replace('-', '_')}"
            self.nodes.append(GraphNode(
                id=dep_id,
                label=f"{dep_name}@{version}",
                type="dependency",
                metadata={"version": version}
            ))
            # Link root project to each dependency
            self.edges.append(GraphEdge(
                source=root_id,
                target=dep_id,
                label="requires"
            ))

            # Add typical dependency relationships (heuristics)
            # E.g. langchain depends on pydantic
            if "langchain" in dep_name.lower() and any("pydantic" in d for d in dependencies):
                pydantic_id = next(f"dep_{d.lower().replace('-', '_')}" for d in dependencies if "pydantic" in d)
                self.edges.append(GraphEdge(
                    source=dep_id,
                    target=pydantic_id,
                    label="depends on"
                ))
