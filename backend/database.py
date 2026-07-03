"""
database.py — SQLAlchemy setup and normalized schemas for YOWON AI.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import DATABASE_URL


# ── Engine & Session factory ──────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class Workspace(Base):
    """Represents an organization or team workspace."""

    __tablename__ = "workspaces"

    workspace_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: str = Column(String(255), nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")


class Project(Base):
    """Represents a user-submitted project pending evaluation."""

    __tablename__ = "projects"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Optional[str] = Column(String(36), ForeignKey("workspaces.workspace_id"), nullable=True, index=True)
    name: str = Column(String(255), nullable=False)
    project_type: str = Column(String(50), nullable=False, default="Hackathon Project")
    description: Optional[str] = Column(Text, nullable=True)
    github_url: Optional[str] = Column(String(512), nullable=True)
    demo_video_url: Optional[str] = Column(String(512), nullable=True)
    pdf_path: Optional[str] = Column(String(512), nullable=True)
    ppt_path: Optional[str] = Column(String(512), nullable=True)

    # Lifecycle
    status: str = Column(String(50), default="pending")  # pending | running | done | failed
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="projects")
    repositories = relationship("Repository", back_populates="project", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="project", cascade="all, delete-orphan")


class Repository(Base):
    """Represents a logical code repository."""

    __tablename__ = "repositories"

    repository_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    github_repository_id: Optional[str] = Column(String(100), nullable=True)
    github_url: str = Column(String(512), nullable=False)
    owner: Optional[str] = Column(String(255), nullable=True)
    repository_name: Optional[str] = Column(String(255), nullable=True)
    default_branch: Optional[str] = Column(String(100), nullable=True)
    visibility: str = Column(String(50), default="public")
    stars: int = Column(Integer, default=0)
    forks: int = Column(Integer, default=0)
    open_issues: int = Column(Integer, default=0)
    license: Optional[str] = Column(String(100), nullable=True)
    topics: Optional[str] = Column(Text, nullable=True)  # JSON list
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="repositories")
    snapshots = relationship("RepositorySnapshot", back_populates="repository", cascade="all, delete-orphan")
    technologies = relationship("Technology", back_populates="repository", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="repository", cascade="all, delete-orphan")


class RepositorySnapshot(Base):
    """Represents the historical state of a repository at a specific commit."""

    __tablename__ = "repository_snapshots"

    snapshot_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: str = Column(String(36), ForeignKey("repositories.repository_id"), nullable=False, index=True)
    commit_sha: str = Column(String(40), nullable=False, index=True)
    tree_sha: Optional[str] = Column(String(40), nullable=True)
    branch: Optional[str] = Column(String(100), nullable=True)
    readme_snapshot: Optional[str] = Column(Text, nullable=True)
    repository_statistics: Optional[str] = Column(Text, nullable=True)  # JSON dict
    folder_structure: Optional[str] = Column(Text, nullable=True)  # JSON list
    technology_summary: Optional[str] = Column(Text, nullable=True)  # JSON dict
    dependency_summary: Optional[str] = Column(Text, nullable=True)  # JSON dict
    architecture_summary: Optional[str] = Column(Text, nullable=True)
    last_commit_timestamp: Optional[datetime] = Column(DateTime, nullable=True)
    snapshot_timestamp: datetime = Column(DateTime, default=datetime.utcnow)
    previous_snapshot_id: Optional[str] = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=True)

    repository = relationship("Repository", back_populates="snapshots")
    evaluations = relationship("Evaluation", back_populates="snapshot", cascade="all, delete-orphan")
    previous_snapshot = relationship("RepositorySnapshot", remote_side=[snapshot_id], backref="next_snapshots")
    files = relationship("RepositoryFile", back_populates="snapshot", cascade="all, delete-orphan")
    folders = relationship("RepositoryFolder", back_populates="snapshot", cascade="all, delete-orphan")


class Technology(Base):
    """Represents a technology framework or library used in a repository."""

    __tablename__ = "technologies"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: str = Column(String(36), ForeignKey("repositories.repository_id"), nullable=False, index=True)
    name: str = Column(String(100), nullable=False, index=True)
    version: Optional[str] = Column(String(50), nullable=True)

    repository = relationship("Repository", back_populates="technologies")


class Dependency(Base):
    """Represents a code dependency mapped from dependency manifests."""

    __tablename__ = "dependencies"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: str = Column(String(36), ForeignKey("repositories.repository_id"), nullable=False, index=True)
    name: str = Column(String(100), nullable=False, index=True)
    version: Optional[str] = Column(String(50), nullable=True)
    type: str = Column(String(50), nullable=False)  # python | npm | maven | go | cargo

    repository = relationship("Repository", back_populates="dependencies")


class RepositoryFile(Base):
    """Represents a file cataloged in a repository snapshot."""

    __tablename__ = "repository_files"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    path: str = Column(String(512), nullable=False)
    size_bytes: int = Column(Integer, default=0)
    language: Optional[str] = Column(String(100), nullable=True)

    snapshot = relationship("RepositorySnapshot", back_populates="files")


class RepositoryFolder(Base):
    """Represents a folder cataloged in a repository snapshot."""

    __tablename__ = "repository_folders"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    path: str = Column(String(512), nullable=False)

    snapshot = relationship("RepositorySnapshot", back_populates="folders")


class Evaluation(Base):
    """Represents a single execution run of project calibration."""

    __tablename__ = "evaluations"

    evaluation_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    repository_snapshot_id: Optional[str] = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=True, index=True)
    timestamp: datetime = Column(DateTime, default=datetime.utcnow, index=True)
    evaluation_duration: Optional[float] = Column(Float, nullable=True)
    overall_score: Optional[float] = Column(Float, nullable=True)
    verdict: Optional[str] = Column(String(20), nullable=True)  # ACCEPT | IMPROVE | REJECT
    confidence: Optional[float] = Column(Float, nullable=True)
    evaluation_status: str = Column(String(20), default="Pending")  # Pending | Running | Completed | Failed | Cancelled

    # Explainable AI & Reproducibility parameters
    llm_model: Optional[str] = Column(String(100), nullable=True)
    embedding_model: Optional[str] = Column(String(100), nullable=True)
    evaluation_version: Optional[str] = Column(String(50), nullable=True)
    prompt_version: Optional[str] = Column(String(50), nullable=True)
    rubric_version: Optional[str] = Column(String(50), nullable=True)

    project = relationship("Project", back_populates="evaluations")
    snapshot = relationship("RepositorySnapshot", back_populates="evaluations")
    agent_evaluations = relationship("AgentEvaluation", back_populates="evaluation", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="evaluation", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="evaluation", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="evaluation", cascade="all, delete-orphan")
    events = relationship("EvaluationEvent", back_populates="evaluation", cascade="all, delete-orphan")


class AgentEvaluation(Base):
    """Stores per-agent evaluation results and timings for a run."""

    __tablename__ = "agent_evaluations"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: str = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False, index=True)
    agent_name: str = Column(String(100), nullable=False, index=True)  # forge | sentinel | visionary | guardian | showcase
    score: Optional[float] = Column(Float, nullable=True)
    confidence: Optional[float] = Column(Float, nullable=True)
    execution_time: Optional[float] = Column(Float, nullable=True)
    summary: Optional[str] = Column(Text, nullable=True)
    status: str = Column(String(50), default="completed")  # completed | failed

    evaluation = relationship("Evaluation", back_populates="agent_evaluations")


class Evidence(Base):
    """Represents a code intelligence evidence line trace for XAI."""

    __tablename__ = "evidence"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: str = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False, index=True)
    category: str = Column(String(50), nullable=False)  # IMPLEMENTATION | SECURITY | ARCHITECTURE | DATABASE | API | ML | DEPLOYMENT | TESTING | DOCUMENTATION
    finding: str = Column(Text, nullable=False)
    file_path: Optional[str] = Column(String(512), nullable=True)
    line_start: Optional[int] = Column(Integer, nullable=True)
    line_end: Optional[int] = Column(Integer, nullable=True)
    confidence: Optional[float] = Column(Float, nullable=True)
    severity: Optional[str] = Column(String(50), nullable=True)  # INFO | LOW | MEDIUM | HIGH | CRITICAL

    evaluation = relationship("Evaluation", back_populates="evidences")
    recommendations = relationship("Recommendation", back_populates="evidence", cascade="all, delete-orphan")


class Recommendation(Base):
    """Tracks action items and expected gains."""

    __tablename__ = "recommendations"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: str = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False, index=True)
    evidence_id: Optional[str] = Column(String(36), ForeignKey("evidence.id"), nullable=True, index=True)
    priority: str = Column(String(20), default="MEDIUM")  # CRITICAL | HIGH | MEDIUM | LOW
    category: Optional[str] = Column(String(100), nullable=True)
    recommendation: str = Column(Text, nullable=False)
    expected_score_gain: Optional[float] = Column(Float, nullable=True)
    estimated_effort: Optional[str] = Column(String(50), nullable=True)
    status: str = Column(String(50), default="Pending")  # Pending | Accepted | Rejected | Implemented | Verified

    evaluation = relationship("Evaluation", back_populates="recommendations")
    evidence = relationship("Evidence", back_populates="recommendations")


class Report(Base):
    """Tracks generated PDF or HTML reports."""

    __tablename__ = "reports"

    report_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: str = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False, index=True)
    report_type: str = Column(String(50), default="PDF")
    file_path: Optional[str] = Column(String(512), nullable=True)
    file_size: Optional[int] = Column(Integer, nullable=True)
    checksum: Optional[str] = Column(String(64), nullable=True)
    generated_at: datetime = Column(DateTime, default=datetime.utcnow)
    generation_time: Optional[float] = Column(Float, nullable=True)
    version: str = Column(String(20), default="1.0.0")

    evaluation = relationship("Evaluation", back_populates="reports")


class EvaluationEvent(Base):
    """Logs evaluation progress events for pipeline timeline replaying."""

    __tablename__ = "evaluation_events"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: str = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False, index=True)
    event_name: str = Column(String(100), nullable=False)
    timestamp: datetime = Column(DateTime, default=datetime.utcnow)
    duration: Optional[float] = Column(Float, nullable=True)
    event_metadata: Optional[str] = Column(Text, nullable=True)  # JSON string
    status: str = Column(String(50), default="completed")  # completed | failed

    evaluation = relationship("Evaluation", back_populates="events")


class RepositoryAnalysis(Base):
    """Represents historical static analysis results cache metadata for a snapshot."""

    __tablename__ = "repository_analyses"

    analysis_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    commit_sha: str = Column(String(40), nullable=False, index=True)
    analysis_version: str = Column(String(50), nullable=False)
    engine_version: str = Column(String(50), nullable=False)
    status: str = Column(String(20), default="Pending")  # Pending | Running | Completed | Failed
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    expires_at: Optional[datetime] = Column(DateTime, nullable=True)

    snapshot = relationship("RepositorySnapshot")


# ── Dependency helper ──────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency that yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
