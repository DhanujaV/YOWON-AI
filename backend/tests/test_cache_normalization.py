import pytest
from unittest.mock import MagicMock
from intelligence.cache_engine import RepositoryAnalysisCache
from intelligence.models import (
    CanonicalTreeDict,
    CanonicalArchitectureDict,
    CanonicalTechnologyDict,
    RepositoryIntelligenceSchemaException
)

def test_canonical_tree_dict_wrapping():
    # Wrap a raw list
    raw_list = [{"name": "main.py", "type": "file"}]
    tree = CanonicalTreeDict(raw_list)
    
    # 1. Must pass isinstance(tree, dict)
    assert isinstance(tree, dict)
    # 2. Must work with len()
    assert len(tree) == 1
    # 3. Must support indexing/slicing
    assert tree[0]["name"] == "main.py"
    # 4. Must support iteration
    names = [node["name"] for node in tree]
    assert names == ["main.py"]

def test_canonical_architecture_dict_wrapping():
    raw_arch = {
        "nodes": [
            {
                "id": "frontend",
                "label": "Frontend",
                "type": "layer",
                "metadata": {"description": "Client UI", "technologies": ["React"], "files": []}
            }
        ],
        "edges": []
    }
    arch = CanonicalArchitectureDict(raw_arch)
    
    # 1. Must pass isinstance(arch, dict)
    assert isinstance(arch, dict)
    # 2. Must lazy expose 'nodes' and 'edges' lists
    assert isinstance(arch.get("nodes"), list)
    assert len(arch.get("nodes")) == 1
    assert arch.get("nodes")[0]["id"] == "frontend"
    # 3. Must expose layers directly as top-level keys for items() iteration
    assert "Frontend" in arch
    assert arch["Frontend"]["description"] == "Client UI"
    
    # 4. items() must return the layer items, not the nodes/edges lists
    keys = list(arch.keys())
    assert "Frontend" in keys
    assert "nodes" not in keys
    assert "edges" not in keys

def test_canonical_technology_dict_wrapping():
    raw_tech = {
        "nodes": [
            {"id": "react", "label": "React", "type": "technology"}
        ],
        "edges": []
    }
    tech = CanonicalTechnologyDict(raw_tech)
    
    assert isinstance(tech, dict)
    assert "React" in tech.get("techs")
    assert tech.get("nodes")[0]["id"] == "react"

def test_cache_validation_raises_exception():
    invalid_data = {
        "repository_tree": 12345, # Invalid: must be list or dict
        "architecture_graph": {},
        "technology_graph": {}
    }
    with pytest.raises(RepositoryIntelligenceSchemaException):
        RepositoryAnalysisCache._validate_and_normalize(invalid_data)
