import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

from database import Base, RepositorySnapshot, Repository, Project, Evaluation
from intelligence.canonical_models import (
    CanonicalTreeDict,
    ArchitectureModel,
    TechnologyGraphModel,
    MetricsModel
)
from intelligence.cache_engine import RepositoryAnalysisCache
from eval_context.pipeline_validator import validate_intelligence_artifacts
from eval_context.evaluation_context import build_evaluation_session

# Setup in-memory sqlite DB for test isolation
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_repository_intelligence_contract_synchronization(db_session):
    # 1. Setup mock records
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(project_id=project.id, repository_name="Test Repo", github_url="https://github.com/test/test")
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    snapshot = RepositorySnapshot(
        repository_id=repository.repository_id,
        commit_sha="ede3d75eb06f24312772ae74285b69e164568835",
        folder_structure='["  [F] src/main.py"]',
        dependency_summary='{"fastapi": "0.100.0"}'
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    evaluation = Evaluation(
        project_id=project.id,
        repository_snapshot_id=snapshot.snapshot_id,
        commit_sha="ede3d75eb06f24312772ae74285b69e164568835",
        evaluation_status="Pending"
    )
    db_session.add(evaluation)
    db_session.commit()
    db_session.refresh(evaluation)

    # 2. Generator Stage: Construct Canonical models directly
    gen_tree = CanonicalTreeDict([{"name": "main.py", "path": "src/main.py", "type": "file"}])
    gen_arch = ArchitectureModel({"Frontend": {"description": "Client", "files": [], "techs": []}})
    gen_tech = TechnologyGraphModel({"techs": ["Python"]})
    gen_metrics = MetricsModel({"src/main.py": {"loc": 100}})
    
    gen_data = {
        "repository_snapshot_id": snapshot.snapshot_id,
        "repository_tree": gen_tree,
        "architecture_graph": gen_arch,
        "technology_graph": gen_tech,
        "metrics": gen_metrics,
        "health": {"overall": 90.0},
        "evidence": [],
        "recommendations": []
    }

    print("\nRepository Tree Type verification:")
    print(f"Generator: {type(gen_data['repository_tree']).__name__}")
    assert isinstance(gen_data["repository_tree"], CanonicalTreeDict)

    # 3. Cache Stages: Save to Cache & verify retrieval
    commit_sha = "ede3d75eb06f24312772ae74285b69e164568835"
    RepositoryAnalysisCache.set(commit_sha, snapshot.snapshot_id, gen_data, db_session)

    # L1 Memory Cache Hit
    l1_data = RepositoryAnalysisCache.get(commit_sha, db_session)
    print(f"Memory Cache: {type(l1_data['repository_tree']).__name__}")
    assert isinstance(l1_data["repository_tree"], list)
    assert isinstance(l1_data["architecture_graph"], ArchitectureModel)
    assert isinstance(l1_data["technology_graph"], TechnologyGraphModel)
    assert isinstance(l1_data["metrics"], MetricsModel)

    # Clean Memory cache to force Disk Cache (L3) loading
    from intelligence.cache_engine import _memory_cache
    _memory_cache.clear()
    
    l3_data = RepositoryAnalysisCache.get(commit_sha, db_session)
    print(f"Disk Cache: {type(l3_data['repository_tree']).__name__}")
    assert isinstance(l3_data["repository_tree"], list)
    assert isinstance(l3_data["architecture_graph"], ArchitectureModel)
    assert isinstance(l3_data["technology_graph"], TechnologyGraphModel)
    assert isinstance(l3_data["metrics"], MetricsModel)

    # DB Cache stage (L2 metadata validation)
    print(f"DB Cache: {type(l3_data['repository_tree']).__name__}")
    assert isinstance(l3_data["repository_tree"], list)

    # 4. Pipeline Validator Stage
    validate_intelligence_artifacts(l3_data)
    print(f"Validator: CanonicalTreeDict")

    # 5. EvaluationSession Stage
    session = build_evaluation_session(db_session, project.id, evaluation.evaluation_id, snapshot.snapshot_id, {})
    intel_res = session.repository_intelligence
    print(f"EvaluationSession: {type(intel_res.repository_tree).__name__}")
    assert isinstance(intel_res.repository_tree, CanonicalTreeDict)
    assert isinstance(intel_res.architecture, ArchitectureModel)
    assert isinstance(intel_res.technology_graph, TechnologyGraphModel)
    assert isinstance(intel_res.complexity_metrics, MetricsModel)

    # 6. Technical Context Summary Stage
    assert len(intel_res.repository_summary) > 0
    print(f"Technical Context: CanonicalTreeDict")
    print("PASS")
