import pytest
from unittest.mock import MagicMock
from intelligence.parsers.parser_registry import ParserRegistry
from intelligence.symbol_indexer import SymbolIndexer
from intelligence.security_engine import SecurityEngine
from intelligence.evidence_engine import EvidenceEngine
from intelligence.architecture_engine import ArchitectureEngine
from intelligence.metrics_engine import MetricsEngine
from intelligence.health_engine import HealthEngine
from intelligence.recommendation_engine import RecommendationEngine

MOCK_PYTHON_CODE = """
import os
import jwt
from fastapi import APIRouter
from sqlalchemy import Column, String

router = APIRouter()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)

@router.get("/users")
def get_users():
    # Helper call
    val = eval("1 + 1")
    key = "secret_api_key_xyz_12345"
    return {"status": "ok"}
"""

def test_python_parser_ast():
    parser = ParserRegistry.get_parser("app/main.py")
    parser.load(MOCK_PYTHON_CODE, "app/main.py")
    assert parser.parse() is True
    
    symbols = parser.get_symbols()
    assert len(symbols) > 0
    # Should detect router route and User model class
    sym_types = [s.type for s in symbols]
    assert "route" in sym_types or "class" in sym_types or "model" in sym_types

    imports = parser.get_imports()
    assert "jwt" in imports
    assert "fastapi" in imports

def test_symbol_indexer():
    indexer = SymbolIndexer()
    indexer.index_file("app/main.py", MOCK_PYTHON_CODE)
    
    all_syms = indexer.get_all_symbols()
    assert len(all_syms) > 0
    
    file_syms = indexer.get_file_symbols("app/main.py")
    assert len(file_syms) == len(all_syms)

    # Test incremental indexing (updating file content)
    indexer.index_file("app/main.py", "class TestClass:\n    pass")
    assert len(indexer.get_all_symbols()) == 1
    assert indexer.get_all_symbols()[0].name == "TestClass"

def test_security_engine():
    engine = SecurityEngine()
    findings = engine.scan_file("app/main.py", MOCK_PYTHON_CODE)
    
    # Should detect raw secrets and unsafe eval() calls
    finding_types = [f["type"] for f in findings]
    assert "secret_leak" in finding_types
    assert "unsafe_api" in finding_types

def test_metrics_engine():
    engine = MetricsEngine()
    findings = [{
        "type": "unsafe_api",
        "rule_id": "RULE_UNSAFE_API_EVAL",
        "file_path": "app/main.py",
        "line_start": 14,
        "line_end": 14,
        "column_start": 4,
        "column_end": 8,
        "description": "Unsafe API call: eval()",
        "severity": "HIGH",
        "confidence": 0.95
    }]
    
    metrics = engine.calculate_file_metrics(
        file_path="app/main.py",
        content=MOCK_PYTHON_CODE,
        symbols=[],
        imports_count=2,
        security_findings=findings,
        has_test_file=True
    )
    
    assert metrics["loc"] > 0
    assert metrics["risk"] > 10 # Boosted by unsafe api finding
    assert metrics["coverage"] == 90 # Map test file is true

def test_health_engine():
    engine = HealthEngine()
    files = ["README.md", "app/main.py", "tests/test_main.py", "Dockerfile"]
    dependencies = {"fastapi": "0.100.0", "pytest": "7.0.0"}
    security_findings = []
    file_metrics = {
        "app/main.py": {"complexity": {"maintainability_index": 85.0}}
    }
    
    health = engine.calculate_health(
        files=files,
        dependencies=dependencies,
        security_findings=security_findings,
        file_metrics=file_metrics
    )
    
    assert health["overall"] > 50
    assert health["documentation"] > 30 # Has README
    assert health["deployment"] > 30 # Has Dockerfile
    assert health["testing"] > 30 # Has test_main.py and pytest
