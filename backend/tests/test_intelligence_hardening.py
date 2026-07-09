import shutil
from pathlib import Path
from unittest.mock import patch
from sqlalchemy.orm import sessionmaker

from database import engine, RepositorySnapshot, Evaluation, RepositoryAnalysis, IntelligenceModuleStatus, Project, Repository
from intelligence.knowledge_graph.knowledge_graph_service import (
    sync_knowledge_graph, get_knowledge_graph_data
)
from intelligence.cache_engine import RepositoryAnalysisCache
from intelligence.intelligence_service import run_repository_intelligence

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_deterministic_id_and_backward_compatibility():
    """Verify that deterministic SHA-256 node IDs are generated and original IDs are correctly mapped back."""
    db = TestingSessionLocal()
    snapshot_id = "test-snapshot-det-1"
    commit_sha = "test-commit-det-1"

    try:
        # Cleanup cache first
        cache_path = Path("repository_cache/analysis_cache") / commit_sha
        if cache_path.exists():
            shutil.rmtree(cache_path)

        # Setup mock project, repository and snapshot in database
        project = Project(id="test-proj-det", name="Det Test Project")
        repo = Repository(repository_id="test-repo-det", project_id="test-proj-det", github_url="https://github.com/mock/repo")
        snapshot = RepositorySnapshot(
            snapshot_id=snapshot_id,
            repository_id="test-repo-det",
            commit_sha=commit_sha,
            folder_structure="[]"
        )
        db.merge(project)
        db.merge(repo)
        db.merge(snapshot)
        db.commit()

        nodes = [
            {"id": "src/main.py", "label": "main.py", "type": "file", "metadata": {}},
            {"id": "src/utils.py", "label": "utils.py", "type": "file", "metadata": {}}
        ]
        edges = [
            {"source": "src/main.py", "target": "src/utils.py", "relation": "IMPORTS"}
        ]

        # Sync to DB
        success = sync_knowledge_graph(db, snapshot_id, commit_sha, nodes, edges)
        assert success is True

        # Retrieve and assert that IDs are mapped back to human-readable format
        graph_data = get_knowledge_graph_data(db, snapshot_id)
        assert len(graph_data["nodes"]) == 2
        assert len(graph_data["edges"]) == 1

        node_ids = {n["id"] for n in graph_data["nodes"]}
        assert "src/main.py" in node_ids
        assert "src/utils.py" in node_ids

        edge = graph_data["edges"][0]
        assert edge["source"] == "src/main.py"
        assert edge["target"] == "src/utils.py"

    finally:
        # Cleanup
        db.query(IntelligenceModuleStatus).delete()
        db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == snapshot_id).delete()
        db.query(Repository).filter(Repository.repository_id == "test-repo-det").delete()
        db.query(Project).filter(Project.id == "test-proj-det").delete()
        db.commit()
        db.close()


def test_cache_case_insensitive_status_and_db_recovery():
    """Verify that lookup resolves analysis regardless of status casing ('Completed' vs 'COMPLETED')."""
    db = TestingSessionLocal()
    commit_sha = "test-commit-cache-case-123"

    try:
        # Mock database record with lowercase 'Completed'
        analysis_lower = RepositoryAnalysis(
            analysis_id="test-analysis-id-lower",
            repository_snapshot_id="test-snapshot-cache-case",
            commit_sha=commit_sha,
            analysis_version=RepositoryAnalysisCache.ANALYSIS_VERSION,
            engine_version=RepositoryAnalysisCache.ENGINE_VERSION,
            status="Completed"
        )
        db.merge(analysis_lower)
        db.commit()

        # Cache lookup should check DB status case-insensitively
        # Mock disk fallback to return dummy data so it does not miss on disk
        with patch.object(RepositoryAnalysisCache, "_load_from_disk", return_value={"repository_snapshot_id": "test-snapshot-cache-case", "evidence": [], "recommendations": []}):
            data = RepositoryAnalysisCache.get(commit_sha, db)
            assert data is not None

        # Repeat with uppercase 'COMPLETED'
        analysis_upper = db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).first()
        analysis_upper.status = "COMPLETED"
        db.commit()

        with patch.object(RepositoryAnalysisCache, "_load_from_disk", return_value={"repository_snapshot_id": "test-snapshot-cache-case", "evidence": [], "recommendations": []}):
            data = RepositoryAnalysisCache.get(commit_sha, db)
            assert data is not None

    finally:
        db.query(RepositoryAnalysis).filter(RepositoryAnalysis.commit_sha == commit_sha).delete()
        db.commit()
        db.close()


def test_module_failure_isolation():
    """Verify that a crash in one static analysis module does not abort the entire pipeline."""
    db = TestingSessionLocal()
    snapshot_id = "test-snapshot-module-fail"
    commit_sha = "test-commit-module-fail"

    # Cleanup cache first
    cache_path = Path("repository_cache/analysis_cache") / commit_sha
    if cache_path.exists():
        shutil.rmtree(cache_path)

    # Setup mock project, repository, snapshot & evaluation
    project = Project(id="test-proj-fail", name="Fail Test Project")
    repo = Repository(repository_id="test-repo-fail", project_id="test-proj-fail", github_url="https://github.com/mock/repo")
    snapshot = RepositorySnapshot(
        snapshot_id=snapshot_id,
        repository_id="test-repo-fail",
        commit_sha=commit_sha,
        folder_structure='["src/main.py"]'
    )
    evaluation = Evaluation(
        evaluation_id="test-eval-module-fail",
        project_id="test-proj-fail",
        evaluation_status="Pending"
    )
    db.merge(project)
    db.merge(repo)
    db.merge(snapshot)
    db.merge(evaluation)
    db.commit()

    try:
        # Mock GitHub cache loader to raise exception, simulating source loading module failure
        with patch("intelligence.repository_scan.RepositoryScan._load_github_cache", side_effect=RuntimeError("GitHub API quota exceeded")):
            # The run should degrade gracefully, loading empty files and successfully finishing analysis instead of crashing
            results = run_repository_intelligence(db, evaluation, snapshot_id)
            print("RESULTS KEYS ARE:", results.keys() if results else None)
            assert results is not None
            assert results.get("repository_snapshot_id") == snapshot_id or "repository_tree" in results

            # Verify that the specific module status was marked as 'failed' in DB
            module_status = db.query(IntelligenceModuleStatus).filter(
                IntelligenceModuleStatus.module_name == "source_loading"
            ).first()
            assert module_status is not None
            assert module_status.status == "failed"
            assert "GitHub API quota" in module_status.error_message

            # Verify that subsequent modules completed successfully
            sym_status = db.query(IntelligenceModuleStatus).filter(
                IntelligenceModuleStatus.module_name == "symbol_indexing"
            ).first()
            assert sym_status is not None
            assert sym_status.status == "completed"

    finally:
        db.query(IntelligenceModuleStatus).delete()
        db.query(RepositoryAnalysis).delete()
        db.query(Evaluation).filter(Evaluation.evaluation_id == "test-eval-module-fail").delete()
        db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == snapshot_id).delete()
        db.query(Repository).filter(Repository.repository_id == "test-repo-fail").delete()
        db.query(Project).filter(Project.id == "test-proj-fail").delete()
        db.commit()
        db.close()
