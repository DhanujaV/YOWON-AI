from intelligence.graph.architecture_graph import ArchitectureGraphBuilder
from intelligence.graph.call_graph import CallGraphBuilder
from intelligence.graph.technology_graph import TechnologyGraphBuilder
from intelligence.health_engine import HealthEngine
from intelligence.metrics_engine import MetricsEngine
from eval_context.context_slicer import slice_context_for_agent

def test_technology_graph_builder():
    builder = TechnologyGraphBuilder()
    techs = ["React", "TypeScript", "Tailwind", "FastAPI", "SQLAlchemy", "SQLite"]
    builder.build(techs)
    
    assert len(builder.nodes) == 6
    labels = {edge.label for edge in builder.edges}
    assert "written in" in labels or "bundled by" in labels or "persists in" in labels
    
def test_architecture_graph_builder():
    builder = ArchitectureGraphBuilder()
    layers = {
        "Frontend": {"description": "Client Web App", "techs": ["React"], "files": ["src/App.tsx"]},
        "Backend": {"description": "FastAPI Server", "techs": ["FastAPI"], "files": ["main.py"]},
        "Database": {"description": "Database Connection", "techs": ["SQLAlchemy"], "files": ["database.py"]}
    }
    builder.build(layers)
    
    assert len(builder.nodes) == 3
    node_ids = {node.id for node in builder.nodes}
    assert "frontend" in node_ids
    assert "backend" in node_ids
    assert "database" in node_ids
    
    edges_sources = {edge.source for edge in builder.edges}
    assert "frontend" in edges_sources
    assert "backend" in edges_sources

def test_call_graph_builder():
    builder = CallGraphBuilder()
    file_imports = {
        "main.py": ["database", "utils"],
        "database.py": ["utils"],
        "utils.py": []
    }
    files = ["main.py", "database.py", "utils.py"]
    builder.build(file_imports, files)
    
    assert len(builder.nodes) == 3
    edges = [(edge.source, edge.target) for edge in builder.edges]
    assert ("main.py", "database.py") in edges or ("database.py", "utils.py") in edges

def test_health_metrics_calc():
    engine = HealthEngine()
    files = ["README.md", "main.py", "tests/test_main.py", "Dockerfile"]
    dependencies = [{"name": "fastapi"}, {"package": "pytest"}]
    security_findings = []
    file_metrics = {"main.py": {"complexity": {"maintainability_index": 85.0}}}
    
    health = engine.calculate_health(files, dependencies, security_findings, file_metrics)
    assert health["overall"] > 50
    assert health["documentation"] > 0
    assert health["testing"] > 0

def test_complexity_analysis_metrics():
    engine = MetricsEngine()
    findings = []
    metrics = engine.calculate_file_metrics(
        file_path="main.py",
        content="def hello():\n    print('world')",
        symbols=[],
        imports_count=1,
        security_findings=findings,
        has_test_file=True
    )
    assert metrics["loc"] == 2
    assert metrics["risk"] >= 0

def test_context_slicer_structured_digest_injection():
    # Construct a project context with repository_intelligence output
    ctx = {
        "project_name": "Test Project",
        "project_type": "Hackathon Project",
        "description": "Mock description",
        "repository_intelligence": {
            "health": {
                "overall": 88,
                "documentation": 70,
                "testing": 80,
                "security": 90,
                "code_quality": 85
            },
            "technology_graph": {
                "nodes": [{"id": "fastapi", "name": "FastAPI", "type": "technology"}]
            },
            "metrics": {
                "main.py": {"loc": 150, "maintainability_index": 85.0}
            },
            "evidence": [
                {"file_path": "main.py", "rule_id": "RULE_FASTAPI_ROUTER", "confidence": 0.95}
            ],
            "recommendations": [
                {"category": "TESTING", "severity": "MEDIUM", "title": "Add tests", "recommendation": "Write more test cases", "expected_score_gain": 5.0}
            ]
        }
    }
    
    # Check technical agent slice
    digest = slice_context_for_agent(ctx, "technical")
    assert "STRUCTURED REPOSITORY INTELLIGENCE DETECTED" in digest
    assert "Overall Codebase Health: 88/100" in digest
    assert "Total Lines of Code (LOC): 150" in digest
    assert "Add tests" in digest
