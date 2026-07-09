from typing import List, Dict, Any, Optional
from pydantic_core import core_schema

class RepositoryIntelligenceSchemaException(Exception):
    """Raised when validation of cached Repository Intelligence schemas fails."""
    pass

class CanonicalTreeDict(dict):
    """
    Canonical Tree representation. Acts as a dictionary (isinstance(x, dict) == True)
    while implementing list operations (length, iteration, slicing) over tree nodes.
    """
    def __init__(self, data: Any):
        if isinstance(data, list):
            self._list = data
            super().__init__(nodes=data)
        elif isinstance(data, dict):
            self._list = data.get("nodes", data.get("tree", []))
            super().__init__(**data)
        else:
            self._list = []
            super().__init__()

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self):
        return iter(self._list)

    def __bool__(self) -> bool:
        return bool(self._list)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, (int, slice)):
            return self._list[key]
        return super().__getitem__(key)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.any_schema(),
            core_schema.no_info_plain_validator_function(cls)
        ])

class ArchitectureModel(dict):
    """
    ArchitectureModel representation. Subclasses dict.
    Exposes top-level layers for summary generator, while lazy-exposing
    'nodes', 'edges', 'layers', and 'modules' for frontend and validators.
    """
    def __init__(self, data: Any):
        if isinstance(data, dict):
            nodes = data.get("nodes") or []
            edges = data.get("edges") or []
            layers_data = data.get("layers") or {}
            
            # Reconstruct layers from nodes if missing
            if not layers_data and nodes:
                layers_data = {}
                for node in nodes:
                    if node.get("type") == "layer":
                        layers_data[node.get("label")] = {
                            "description": node.get("metadata", {}).get("description", ""),
                            "files": node.get("metadata", {}).get("files", []),
                            "techs": node.get("metadata", {}).get("technologies", [])
                        }
            # Reconstruct nodes from layers if missing
            elif not nodes and layers_data:
                nodes = []
                for label, info in layers_data.items():
                    nodes.append({
                        "id": label.lower(),
                        "label": label,
                        "type": "layer",
                        "metadata": {
                            "description": info.get("description", ""),
                            "technologies": info.get("techs", []),
                            "files": info.get("files", [])
                        }
                    })
            
            self._layers = layers_data
            self._nodes = nodes
            self._edges = edges
            self._modules = []
            
            super().__init__(**layers_data)
        else:
            self._layers = {}
            self._nodes = []
            self._edges = []
            self._modules = []
            super().__init__()

    def __getitem__(self, key: Any) -> Any:
        if key == "nodes":
            return self._nodes
        if key == "edges":
            return self._edges
        if key == "layers":
            return self._layers
        if key == "modules":
            return self._modules
        return super().__getitem__(key)

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        if key == "nodes":
            return self._nodes
        if key == "edges":
            return self._edges
        if key == "layers":
            return self._layers
        if key == "modules":
            return self._modules
        return super().get(key, default)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.any_schema(),
            core_schema.no_info_plain_validator_function(cls)
        ])

class TechnologyGraphModel(dict):
    """
    TechnologyGraphModel representation. Subclasses dict.
    Ensures 'nodes', 'edges', 'techs', 'frameworks', 'languages', and 'tools'
    are consistently present and validated.
    """
    def __init__(self, data: Any):
        if isinstance(data, dict):
            techs = data.get("techs") or []
            frameworks = data.get("frameworks") or []
            languages = data.get("languages") or []
            tools = data.get("tools") or []
            nodes = data.get("nodes") or []
            edges = data.get("edges") or []
            
            if not techs and nodes:
                techs = [n.get("label") or n.get("id") for n in nodes if n.get("type") == "technology"]
            if not nodes and techs:
                nodes = [{"id": t.lower(), "label": t, "type": "technology"} for t in techs]
                
            self._techs = techs
            self._frameworks = frameworks
            self._languages = languages
            self._tools = tools
            self._nodes = nodes
            self._edges = edges
            
            super().__init__(
                techs=techs,
                frameworks=frameworks,
                languages=languages,
                tools=tools
            )
        else:
            self._techs = []
            self._frameworks = []
            self._languages = []
            self._tools = []
            self._nodes = []
            self._edges = []
            super().__init__()

    def __getitem__(self, key: Any) -> Any:
        if key == "nodes":
            return self._nodes
        if key == "edges":
            return self._edges
        return super().__getitem__(key)

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        if key == "nodes":
            return self._nodes
        if key == "edges":
            return self._edges
        return super().get(key, default)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.any_schema(),
            core_schema.no_info_plain_validator_function(cls)
        ])

class MetricsModel(dict):
    """
    MetricsModel representation. Subclasses dict.
    Provides standard metrics interface.
    """
    def __init__(self, data: Any):
        if isinstance(data, dict):
            super().__init__(**data)
        else:
            super().__init__()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.any_schema(),
            core_schema.no_info_plain_validator_function(cls)
        ])
