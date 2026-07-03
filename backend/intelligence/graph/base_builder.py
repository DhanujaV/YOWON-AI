from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from intelligence.models import GraphNode, GraphEdge

class BaseGraphBuilder(ABC):
    def __init__(self):
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []

    @abstractmethod
    def build(self, *args, **kwargs) -> None:
        """Abstract method to construct nodes and edges."""
        pass

    def serialize(self) -> Dict[str, Any]:
        """Convert graph into standard JSON-compatible dict."""
        return {
            "nodes": [n.model_dump() for n in self.nodes],
            "edges": [e.model_dump() for e in self.edges]
        }

    def search(self, query: str) -> List[str]:
        """Return list of node IDs matching query string."""
        q = query.lower()
        matched = []
        for n in self.nodes:
            if q in n.label.lower() or q in n.id.lower() or q in n.type.lower():
                matched.append(n.id)
        return matched

    def filter(self, node_types: List[str]) -> Dict[str, Any]:
        """Return a sub-graph containing only nodes of specified types."""
        filtered_nodes = [n for n in self.nodes if n.type in node_types]
        node_ids = {n.id for n in filtered_nodes}
        filtered_edges = [e for e in self.edges if e.source in node_ids and e.target in node_ids]
        return {
            "nodes": [n.model_dump() for n in filtered_nodes],
            "edges": [e.model_dump() for e in filtered_edges]
        }

    def highlight(self, target_id: str) -> Dict[str, Any]:
        """Returns visual updates marking direct neighbors of target_id."""
        highlighted_nodes = {target_id}
        for e in self.edges:
            if e.source == target_id:
                highlighted_nodes.add(e.target)
            elif e.target == target_id:
                highlighted_nodes.add(e.source)
        return {
            "highlighted_nodes": list(highlighted_nodes),
            "target_node": target_id
        }
