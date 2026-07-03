from typing import Dict, Any, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder

TECH_RELATIONS = [
    ("react", "vite", "bundled by"),
    ("react", "typescript", "written in"),
    ("react", "tailwind", "styled with"),
    ("fastapi", "sqlalchemy", "queries via"),
    ("sqlalchemy", "postgresql", "persists in"),
    ("sqlalchemy", "sqlite", "persists in"),
    ("langchain", "ollama", "orchestrates"),
    ("langchain", "chromadb", "stores vectors in"),
]

class TechnologyGraphBuilder(BaseGraphBuilder):
    def build(self, techs: List[str]) -> None:
        """Constructs Technology Graph showing relations between detected technologies."""
        self.nodes = []
        self.edges = []
        
        # Add nodes
        tech_set = {t.lower() for t in techs}
        for t in techs:
            self.nodes.append(GraphNode(
                id=t.lower(),
                label=t,
                type="technology"
            ))
            
        # Add edges based on relations
        node_ids = {n.id for n in self.nodes}
        for src, dest, label in TECH_RELATIONS:
            if src in node_ids and dest in node_ids:
                self.edges.append(GraphEdge(
                    source=src,
                    target=dest,
                    label=label
                ))
