from typing import Dict, Any, List
from intelligence.models import GraphNode, GraphEdge
from intelligence.graph.base_builder import BaseGraphBuilder


# Standard architectural flow links between detected layers
_ARCH_FLOW_LINKS = [
    ("presentation", "api",           "Sends HTTP requests to"),
    ("api",          "controllers",   "Delegates handling to"),
    ("controllers",  "services",      "Calls business logic in"),
    ("services",     "repositories",  "Accesses data via"),
    ("repositories", "models",        "Maps entities through"),
    ("models",       "database",      "Persists schema in"),
    ("api",          "authentication","Validates identity via"),
    ("authentication", "authorization","Checks permissions in"),
    ("controllers",  "caching",       "Reads hot data from"),
    ("services",     "workers",       "Dispatches jobs to"),
    ("services",     "ai_agents",     "Orchestrates AI through"),
    ("ai_agents",    "llm_providers", "Invokes models via"),
    ("ai_agents",    "memory",        "Retrieves context from"),
    ("ai_agents",    "prompt_manager","Formats prompts using"),
    ("ai_agents",    "retriever",     "Retrieves documents via"),
    ("llm_providers","ai_agents",     "Returns completions to"),
    ("services",     "monitoring",    "Reports telemetry to"),
    ("runtime",      "api",           "Serves requests via"),
    ("configuration","services",      "Injects settings into"),
    ("deployment",   "runtime",       "Packages and starts"),
    ("infrastructure","deployment",   "Provisions environment for"),
    ("testing",      "services",      "Validates behavior of"),
    ("sandbox",      "ai_agents",     "Provides execution env to"),
]


class ArchitectureGraphBuilder(BaseGraphBuilder):
    def build(self, layers: Dict[str, Any]) -> None:
        """
        Constructs Architecture Graph from dynamically analyzed layers.
        Passes all rich metadata fields (health, risk, purpose, responsibilities,
        inputs, outputs, consumers, providers, evidence, complexity, confidence).
        """
        self.nodes = []
        self.edges = []

        # Create nodes for detected layers — pass ALL metadata from ArchitectureEngine
        for layer_name, data in layers.items():
            node_id = layer_name.lower().replace(" ", "_")
            self.nodes.append(GraphNode(
                id=node_id,
                label=layer_name,
                type="layer",
                metadata={
                    "description":      data.get("description", ""),
                    "technologies":     data.get("techs", []),
                    "files":            data.get("files", []),
                    # Rich v3 fields for the inspector panel
                    "purpose":          data.get("purpose", data.get("description", "")),
                    "responsibilities": data.get("responsibilities", []),
                    "inputs":           data.get("inputs", "Internal method parameters"),
                    "outputs":          data.get("outputs", "Data object return values"),
                    "consumers":        data.get("consumers", []),
                    "providers":        data.get("providers", []),
                    "health":           data.get("health", 80.0),
                    "risk":             data.get("risk", 20.0),
                    "complexity":       data.get("complexity", 0.0),
                    "confidence":       data.get("confidence", 0.75),
                    "summary":          data.get("summary", f"Architecture layer: {layer_name}"),
                    "evidence":         data.get("evidence", []),
                    "ownership":        data.get("ownership", "Engineering Team"),
                }
            ))

        # Link layers using standard architectural flow definitions
        node_ids = {n.id for n in self.nodes}

        for src, dest, label in _ARCH_FLOW_LINKS:
            if src in node_ids and dest in node_ids:
                self.edges.append(GraphEdge(
                    source=src,
                    target=dest,
                    label=label,
                ))
