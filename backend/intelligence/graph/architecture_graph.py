from typing import Dict, Any, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder

class ArchitectureGraphBuilder(BaseGraphBuilder):
    def build(self, layers: Dict[str, Any]) -> None:
        """Constructs Architecture Graph from dynamically analyzed layers."""
        self.nodes = []
        self.edges = []

        # Create nodes for detected layers
        for layer_name, data in layers.items():
            self.nodes.append(GraphNode(
                id=layer_name.lower(),
                label=layer_name,
                type="layer",
                metadata={
                    "description": data["description"],
                    "technologies": data["techs"],
                    "files": data["files"]
                }
            ))

        # Sequentially link detected layers based on architectural pipeline flows
        node_ids = {n.id for n in self.nodes}
        
        links_seq = [
            ("frontend", "backend", "Sends requests to"),
            ("backend", "database", "Queries/Writes to"),
            ("backend", "inference", "Invokes predictions from"),
            ("inference", "database", "Retrieves context/embeds"),
            ("backend", "workers", "Enqueues background jobs to"),
            ("workers", "database", "Updates job state in"),
            ("backend", "deployment", "Configures container for")
        ]
        
        for src, dest, label in links_seq:
            if src in node_ids and dest in node_ids:
                self.edges.append(GraphEdge(
                    source=src,
                    target=dest,
                    label=label
                ))
