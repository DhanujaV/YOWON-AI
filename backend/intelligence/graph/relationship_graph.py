from typing import Dict, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder

class RelationshipGraphBuilder(BaseGraphBuilder):
    def build(self, files: List[str], dependencies: Dict[str, str]) -> None:
        """Constructs a general relationship graph between files and their top-level dependency categories."""
        self.nodes = []
        self.edges = []

        # Simple file-to-dependency mapping for high-level structure
        root_id = "repository"
        self.nodes.append(GraphNode(
            id=root_id,
            label="Repository",
            type="root"
        ))

        # Add nodes for file groups
        file_exts = {f.split(".")[-1].lower() for f in files if "." in f}
        for ext in file_exts:
            ext_id = f"ext_{ext}"
            self.nodes.append(GraphNode(
                id=ext_id,
                label=f"{ext.upper()} Files",
                type="group"
            ))
            self.edges.append(GraphEdge(
                source=root_id,
                target=ext_id,
                label="contains"
            ))
