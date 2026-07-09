"""
tests/test_history.py — Test suite for normalized database models, relation integrity, comparison engine, and webhook APIs.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import (
    Base,
    Project,
    Repository,
    RepositorySnapshot,
    Evaluation,
    AgentEvaluation,
    Evidence,
    Recommendation,
    Report,
    get_db,
)

# Setup temp SQLite file DB for test isolation
TEST_DATABASE_URL = "sqlite:///test_temp.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_temp.db"):
        try:
            os.remove("test_temp.db")
        except Exception:
            pass


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_normalized_database_relations():
    db = TestingSessionLocal()
    try:
        # 1. Create Project
        project = Project(
            id=str(uuid.uuid4()),
            name="Sentient AI Hub",
            project_type="Machine Learning",
            description="Agentic framework",
            status="pending"
        )
        db.add(project)
        db.commit()

        # 2. Create Repository
        repo = Repository(
            repository_id=str(uuid.uuid4()),
            project_id=project.id,
            github_repository_id="99812",
            github_url="https://github.com/test/sentient-hub",
            owner="test",
            repository_name="sentient-hub",
            default_branch="main",
            visibility="public",
            stars=12,
            forks=2
        )
        db.add(repo)
        db.commit()

        # 3. Create RepositorySnapshot
        snapshot = RepositorySnapshot(
            snapshot_id=str(uuid.uuid4()),
            repository_id=repo.repository_id,
            commit_sha="c0ff3e",
            tree_sha="ab12cd",
            branch="main",
            repository_statistics=json.dumps({"total_files": 12, "code_files": 8}),
            snapshot_timestamp=datetime.utcnow()
        )
        db.add(snapshot)
        db.commit()

        # 4. Create Evaluation
        evaluation = Evaluation(
            evaluation_id=str(uuid.uuid4()),
            project_id=project.id,
            repository_snapshot_id=snapshot.snapshot_id,
            timestamp=datetime.utcnow(),
            evaluation_duration=12.5,
            overall_score=88.5,
            verdict="ACCEPT",
            confidence=0.92,
            evaluation_status="Completed"
        )
        db.add(evaluation)
        db.commit()

        # 5. Create AgentEvaluation
        agent_eval = AgentEvaluation(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            agent_name="forge",
            score=90.0,
            confidence=0.95,
            execution_time=4.2,
            summary="Clean architecture and solid modular structure.",
            status="completed"
        )
        db.add(agent_eval)
        db.commit()

        # 6. Create Evidence
        evidence = Evidence(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            category="SECURITY",
            finding="Hardcoded secret found in auth middleware",
            file_path="src/middleware.py",
            line_start=12,
            line_end=15,
            confidence=0.98,
            severity="HIGH"
        )
        db.add(evidence)
        db.commit()

        # 7. Create Recommendation
        recommendation = Recommendation(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            evidence_id=evidence.id,
            priority="HIGH",
            category="SECURITY",
            recommendation="Use env vars instead of hardcoded token",
            expected_score_gain=6.5,
            status="Pending"
        )
        db.add(recommendation)
        db.commit()

        # 8. Create Report
        report = Report(
            report_id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            report_type="PDF",
            file_path="/tmp/report.pdf",
            checksum="sha-checksum-hash",
            version="1.0.0"
        )
        db.add(report)
        db.commit()

        # Check relationships integrity
        queried_project = db.query(Project).filter(Project.id == project.id).first()
        assert len(queried_project.repositories) == 1
        assert queried_project.repositories[0].repository_name == "sentient-hub"

        queried_eval = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation.evaluation_id).first()
        assert queried_eval.snapshot.commit_sha == "c0ff3e"
        assert len(queried_eval.agent_evaluations) == 1
        assert queried_eval.agent_evaluations[0].agent_name == "forge"
        assert len(queried_eval.evidences) == 1
        assert queried_eval.evidences[0].severity == "HIGH"
        assert len(queried_eval.recommendations) == 1
        assert queried_eval.recommendations[0].priority == "HIGH"
        assert len(queried_eval.reports) == 1
        assert queried_eval.reports[0].checksum == "sha-checksum-hash"

    finally:
        db.close()


def test_comparison_endpoint():
    db = TestingSessionLocal()
    try:
        # Create Project
        project = Project(
            id=str(uuid.uuid4()),
            name="Sign Language Detector",
            project_type="Computer Vision",
            status="done"
        )
        db.add(project)
        db.commit()

        # Create Repositories
        repo = Repository(
            repository_id=str(uuid.uuid4()),
            project_id=project.id,
            github_url="https://github.com/user/sign-detector"
        )
        db.add(repo)
        db.commit()

        # Create Snapshots
        snap_old = RepositorySnapshot(
            snapshot_id=str(uuid.uuid4()),
            repository_id=repo.repository_id,
            commit_sha="old-commit-123",
            technology_summary=json.dumps([{"name": "Python"}, {"name": "Numpy"}]),
            dependency_summary=json.dumps([{"name": "numpy", "version": "1.21.0"}]),
            repository_statistics=json.dumps({"repository_completeness_score": 60.0})
        )
        snap_new = RepositorySnapshot(
            snapshot_id=str(uuid.uuid4()),
            repository_id=repo.repository_id,
            commit_sha="new-commit-456",
            technology_summary=json.dumps([{"name": "Python"}, {"name": "Numpy"}, {"name": "FastAPI"}]),
            dependency_summary=json.dumps([{"name": "numpy", "version": "1.21.0"}, {"name": "fastapi", "version": "0.80.0"}]),
            repository_statistics=json.dumps({"repository_completeness_score": 85.0})
        )
        db.add(snap_old)
        db.add(snap_new)
        db.commit()

        # Create Evaluations
        eval_old = Evaluation(
            evaluation_id=str(uuid.uuid4()),
            project_id=project.id,
            repository_snapshot_id=snap_old.snapshot_id,
            overall_score=70.0,
            verdict="IMPROVE",
            evaluation_status="Completed"
        )
        eval_new = Evaluation(
            evaluation_id=str(uuid.uuid4()),
            project_id=project.id,
            repository_snapshot_id=snap_new.snapshot_id,
            overall_score=85.0,
            verdict="ACCEPT",
            evaluation_status="Completed"
        )
        db.add(eval_old)
        db.add(eval_new)
        db.commit()

        # Create Agent Evaluations
        db.add(AgentEvaluation(
            id=str(uuid.uuid4()),
            evaluation_id=eval_old.evaluation_id,
            agent_name="forge",
            score=70.0
        ))
        db.add(AgentEvaluation(
            id=str(uuid.uuid4()),
            evaluation_id=eval_new.evaluation_id,
            agent_name="forge",
            score=85.0
        ))
        
        # Create Evidence and Recommendations
        db.add(Evidence(
            id=str(uuid.uuid4()),
            evaluation_id=eval_old.evaluation_id,
            category="SECURITY",
            finding="SQL Injection vulnerability"
        ))
        db.add(Recommendation(
            id=str(uuid.uuid4()),
            evaluation_id=eval_old.evaluation_id,
            recommendation="Fix SQL injection"
        ))
        db.commit()

        # Request comparison endpoint
        response = client.get(f"/evaluations/{eval_new.evaluation_id}/compare/{eval_old.evaluation_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Validate differences calculations
        assert data["score_difference"] == 15.0
        assert data["verdict_changed"] is True
        assert data["verdict_new"] == "ACCEPT"
        assert data["verdict_old"] == "IMPROVE"
        assert data["agent_scores_difference"]["forge"] == 15.0
        assert "FastAPI" in data["technologies"]["added"]
        assert "fastapi" in data["dependencies"]["added"]
        assert data["completeness_score_difference"] == 25.0
        assert "SQL Injection vulnerability" in data["risks"]["resolved"]
        assert "Fix SQL injection" in data["recommendations"]["resolved"]

    finally:
        db.close()


def test_github_webhook():
    db = TestingSessionLocal()
    try:
        # Create matching Project
        project = Project(
            id=str(uuid.uuid4()),
            name="Repo Scanner",
            project_type="Web App",
            github_url="https://github.com/coder/repo-scanner",
            status="done"
        )
        db.add(project)
        db.commit()

        # Send GitHub webhook mock push request
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "id": 123456,
                "html_url": "https://github.com/coder/repo-scanner"
            },
            "head_commit": {
                "id": "abcdef1234567890"
            }
        }
        headers = {
            "X-GitHub-Event": "push",
            "Content-Type": "application/json"
        }
        response = client.post("/webhooks/github", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "triggered evaluation"
        
    finally:
        db.close()


def test_report_endpoint_hardening():
    db = TestingSessionLocal()
    try:
        # Create Project
        project = Project(
            id=str(uuid.uuid4()),
            name="Harden Test Project",
            project_type="Web App",
            status="done"
        )
        db.add(project)
        db.commit()

        # Create Evaluation
        evaluation = Evaluation(
            evaluation_id=str(uuid.uuid4()),
            project_id=project.id,
            evaluation_status="Completed",
            overall_score=85.0,
            verdict="ACCEPT",
            timestamp=datetime.utcnow()
        )
        db.add(evaluation)
        db.commit()

        # Create AgentEvaluation with malformed/unparseable findings (Issue 4)
        ae = AgentEvaluation(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            agent_name="chief_evaluation",
            score=85.0,
            confidence=0.9,
            execution_time=1.2,
            summary="This is raw LLM text with no json markdown block and malformed dict structures that normally crash simple parsers.",
            status="SUCCESS"
        )
        db.add(ae)

        # Create Report object (to test report attribute lookups when report is not None)
        report = Report(
            report_id=str(uuid.uuid4()),
            evaluation_id=evaluation.evaluation_id,
            report_type="PDF",
            file_path="/tmp/report.pdf",
            checksum="sha-checksum",
            version="1.0.0"
        )
        db.add(report)
        db.commit()

        # Trigger GET /report/{project_id}
        response = client.get(f"/report/{project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project.id
        assert data["overall_score"] == 85.0
        assert data["verdict"] == "ACCEPT"
        assert data["verdict_data"]["overall_score"] == 85.0
        assert data["verdict_data"]["executive_summary"] is not None

    finally:
        db.close()
