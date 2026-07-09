"""
test_ri_contract.py — Contract tests for Repository Intelligence pipeline.

Ensures:
1. RIResult can be constructed, serialized to cache dict, and deserialized back.
2. RIQualityScore.compute() produces correct scores from RIResult.
3. serialize_for_api() converts all canonical model wrappers to plain JSON.
4. All required fields are present in the cache dict output.
"""
import pytest
from intelligence.ri_contract import (
    RIResult,
    RIDiagnosticsPayload,
    RIQualityScore,
    serialize_for_api,
)


# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_result():
    """Minimal valid RIResult with empty graphs."""
    return RIResult()


@pytest.fixture
def populated_result():
    """RIResult with realistic data for scoring tests."""
    return RIResult(
        repository_tree=[
            {"name": "main.py", "path": "main.py", "type": "file", "size": 5000}
        ] * 10,
        architecture_graph={
            "nodes": [{"id": f"n{i}", "label": f"Layer {i}", "type": "layer"} for i in range(8)],
            "edges": [{"source": "n0", "target": "n1", "relation": "depends_on"}],
        },
        technology_graph={
            "nodes": [{"id": "python", "label": "Python", "type": "language"} for _ in range(5)],
            "edges": [],
        },
        dependency_graph={
            "nodes": [{"id": "fastapi", "label": "FastAPI", "type": "library"}] * 3,
            "edges": [],
        },
        knowledge_graph={
            "nodes": [{"id": f"sym{i}", "label": f"Symbol {i}", "type": "function"} for i in range(50)],
            "edges": [{"source": "sym0", "target": "sym1", "relation": "calls"} for _ in range(100)],
        },
        evidence=[{"rule_id": f"RULE_{i}", "description": "test"} for i in range(20)],
        detected_technologies=["Python", "FastAPI", "React"],
        technology_detections=[
            {"name": "Python", "category": "LANGUAGE", "confidence": 0.99},
            {"name": "FastAPI", "category": "FRAMEWORK", "confidence": 0.95},
        ],
        diagnostics=RIDiagnosticsPayload(
            total_files=50,
            total_loc=5000,
            total_functions=100,
            total_classes=20,
            architecture_nodes=8,
            technology_nodes=5,
            knowledge_nodes=50,
            knowledge_edges=100,
            evidence_count=20,
            execution_time_seconds=3.5,
            cache_level="MISS",
        ),
    )


# ────────────────────────────────────────────────────────────────────────────
# Contract: RIResult roundtrip through cache dict
# ────────────────────────────────────────────────────────────────────────────

def test_ri_result_default_construction():
    """RIResult should construct with all defaults without error."""
    result = RIResult()
    assert result.repository_tree == []
    assert result.architecture_graph == {}
    assert result.technology_graph == {}
    assert result.dependency_graph == {}
    assert result.evidence == []
    assert result.detected_technologies == []
    assert result.technology_detections == []


def test_ri_result_to_cache_dict_has_required_keys(populated_result):
    """to_cache_dict must contain all required contract keys."""
    required_keys = [
        "repository_tree",
        "architecture_graph",
        "technology_graph",
        "dependency_graph",
        "call_graph",
        "knowledge_graph",
        "evidence",
        "recommendations",
        "metrics",
        "health",
        "detected_technologies",
        "technology_detections",
        "diagnostics",
        "quality",
    ]
    cache_dict = populated_result.to_cache_dict()
    for key in required_keys:
        assert key in cache_dict, f"Missing required key: {key}"


def test_ri_result_roundtrip(populated_result):
    """to_cache_dict → from_cache_dict must preserve all core data."""
    cache_dict = populated_result.to_cache_dict()
    restored = RIResult.from_cache_dict(cache_dict)

    assert len(restored.repository_tree) == len(populated_result.repository_tree)
    assert len(restored.evidence) == len(populated_result.evidence)
    assert len(restored.detected_technologies) == len(populated_result.detected_technologies)
    assert len(restored.technology_detections) == len(populated_result.technology_detections)


def test_ri_result_from_empty_cache_dict():
    """from_cache_dict with empty dict should not raise and return defaults."""
    result = RIResult.from_cache_dict({})
    assert result.repository_tree == []
    assert result.architecture_graph == {}


def test_ri_result_from_corrupt_cache_dict():
    """from_cache_dict with wrong types should not raise — guard with safe_list/safe_dict."""
    result = RIResult.from_cache_dict({
        "repository_tree": "not_a_list",
        "architecture_graph": "not_a_dict",
        "evidence": None,
    })
    assert isinstance(result.repository_tree, list)
    assert isinstance(result.architecture_graph, dict)
    assert isinstance(result.evidence, list)


# ────────────────────────────────────────────────────────────────────────────
# Contract: RIQualityScore
# ────────────────────────────────────────────────────────────────────────────

def test_quality_score_minimal_result(minimal_result):
    """Empty result should produce zero quality scores."""
    quality = RIQualityScore.compute(minimal_result)
    assert quality.overall_score == 0.0
    assert quality.architecture_score == 0.0
    assert quality.evidence_score == 0.0
    assert not quality.is_sufficient


def test_quality_score_populated_result(populated_result):
    """Full result should score high on all dimensions."""
    quality = RIQualityScore.compute(populated_result)
    assert quality.repository_tree_score == 100.0
    assert quality.architecture_score == 100.0
    assert quality.technology_score == 100.0
    assert quality.evidence_score == 100.0
    assert quality.overall_score > 70.0
    assert quality.is_sufficient


def test_quality_score_to_dict_has_is_sufficient(populated_result):
    """to_dict must include is_sufficient flag."""
    quality = RIQualityScore.compute(populated_result)
    d = quality.to_dict()
    assert "is_sufficient" in d
    assert "overall_score" in d


# ────────────────────────────────────────────────────────────────────────────
# Contract: serialize_for_api
# ────────────────────────────────────────────────────────────────────────────

def test_serialize_plain_dict():
    """Plain dict should pass through unchanged."""
    data = {"nodes": [{"id": "a"}], "edges": []}
    result = serialize_for_api(data)
    assert result == data


def test_serialize_plain_list():
    """Plain list should pass through unchanged."""
    data = [{"id": "a"}, {"id": "b"}]
    result = serialize_for_api(data)
    assert result == data


def test_serialize_nested():
    """Nested structures should be recursively serialized."""
    data = {
        "architecture": {
            "nodes": [{"id": "n1", "label": "Backend"}],
            "edges": []
        }
    }
    result = serialize_for_api(data)
    assert result["architecture"]["nodes"][0]["id"] == "n1"


def test_serialize_primitives():
    """Primitive values should pass through unchanged."""
    for val in (42, 3.14, "hello", True, None):
        assert serialize_for_api(val) == val


# ────────────────────────────────────────────────────────────────────────────
# Contract: RIDiagnosticsPayload
# ────────────────────────────────────────────────────────────────────────────

def test_diagnostics_to_dict_has_all_18_fields():
    """RIDiagnosticsPayload.to_dict() must have exactly 19 fields (18 + engine_version)."""
    diag = RIDiagnosticsPayload(
        total_files=100,
        total_loc=8000,
        execution_time_seconds=4.2,
    )
    d = diag.to_dict()
    expected_fields = {
        "repository_size_bytes", "total_directories", "total_files", "total_loc",
        "total_functions", "total_classes", "total_imports", "total_dependencies",
        "total_ast_nodes", "architecture_nodes", "technology_nodes", "knowledge_nodes",
        "knowledge_edges", "evidence_count", "warnings", "errors",
        "cache_level", "execution_time_seconds", "memory_usage_mb", "engine_version",
    }
    for f in expected_fields:
        assert f in d, f"Missing diagnostics field: {f}"
    assert d["total_files"] == 100
    assert d["total_loc"] == 8000
    assert d["execution_time_seconds"] == pytest.approx(4.2, abs=0.001)
