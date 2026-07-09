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
    Boolean,
    UniqueConstraint,
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

    # Extended Versioning & Integrity metadata
    analysis_engine_version: Optional[str] = Column(String(50), nullable=True)
    parser_version: Optional[str] = Column(String(50), nullable=True)
    rule_registry_version: Optional[str] = Column(String(50), nullable=True)
    scoring_version: Optional[str] = Column(String(50), nullable=True)
    evaluation_session_version: Optional[str] = Column(String(50), nullable=True)

    # Snapshot Fingerprint
    repository_fingerprint: Optional[str] = Column(String(64), nullable=True)
    commit_sha: Optional[str] = Column(String(40), nullable=True)
    tree_sha: Optional[str] = Column(String(40), nullable=True)
    default_branch: Optional[str] = Column(String(100), nullable=True)
    repository_hash: Optional[str] = Column(String(64), nullable=True)
    snapshot_timestamp: Optional[datetime] = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="evaluations")
    snapshot = relationship("RepositorySnapshot", back_populates="evaluations")
    agent_evaluations = relationship("AgentEvaluation", back_populates="evaluation", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="evaluation", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="evaluation", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="evaluation", cascade="all, delete-orphan")
    events = relationship("EvaluationEvent", back_populates="evaluation", cascade="all, delete-orphan")
    provenance = relationship("ScoreProvenance", back_populates="evaluation", cascade="all, delete-orphan")
    stage_timings = relationship("PipelineStageTiming", back_populates="evaluation", cascade="all, delete-orphan")
    prompt_metrics = relationship("AgentPromptMetric", back_populates="evaluation", cascade="all, delete-orphan")
    diagnostics = relationship("PipelineDiagnostic", back_populates="evaluation", cascade="all, delete-orphan")
    audits = relationship("EvaluationAudit", back_populates="evaluation", cascade="all, delete-orphan")


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
    report_status: Optional[str] = Column(String(20), default="ready")
    report_error: Optional[str] = Column(Text, nullable=True)

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


class KnowledgeGraphNode(Base):
    """Represents a node in the repository knowledge graph."""

    __tablename__ = "knowledge_graph_nodes"

    node_id: str = Column(String(100), primary_key=True)
    repository_snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    commit_sha: str = Column(String(40), nullable=False, index=True)
    label: str = Column(String(200), nullable=False)
    type: str = Column(String(50), nullable=False)  # file | class | function | api | model | service | controller | library | env_var | docker_service
    metadata_json: Optional[str] = Column(Text, nullable=True)  # JSON fields: description, metrics, evidence, recommendations, agent_comments, etc.

    snapshot = relationship("RepositorySnapshot")


class KnowledgeGraphEdge(Base):
    """Represents a directed link/edge in the repository knowledge graph."""

    __tablename__ = "knowledge_graph_edges"

    edge_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    commit_sha: str = Column(String(40), nullable=False, index=True)
    source: str = Column(String(100), nullable=False, index=True)
    target: str = Column(String(100), nullable=False, index=True)
    relation: str = Column(String(50), nullable=False)  # IMPORTS | CALLS | INHERITS | IMPLEMENTS | USES | CONNECTS_TO | DEPENDS_ON | GENERATES

    snapshot = relationship("RepositorySnapshot")


class RepositoryAnalysis(Base):
    """Represents historical static analysis results cache metadata for a snapshot."""

    __tablename__ = "repository_analyses"

    analysis_id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_snapshot_id: str = Column(String(36), ForeignKey("repository_snapshots.snapshot_id"), nullable=False, index=True)
    commit_sha: str = Column(String(40), nullable=False, index=True, unique=True)
    analysis_version: str = Column(String(50), nullable=False)
    engine_version: str = Column(String(50), nullable=False)
    status: str = Column(String(50), default="Pending")  # e.g., QUEUED, Running, Completed, Failed
    current_stage: Optional[str] = Column(String(100), nullable=True)
    progress: int = Column(Integer, default=0)
    started_at: Optional[datetime] = Column(DateTime, nullable=True)
    ended_at: Optional[datetime] = Column(DateTime, nullable=True)
    duration: Optional[float] = Column(Float, nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    completed_stages: Optional[str] = Column(Text, nullable=True)  # JSON-serialized list of stages completed
    files_processed: int = Column(Integer, default=0)
    current_module: Optional[str] = Column(String(100), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    expires_at: Optional[datetime] = Column(DateTime, nullable=True)

    snapshot = relationship("RepositorySnapshot")


class IntelligenceModuleStatus(Base):
    """Tracks status, timings and stats of individual Repository Intelligence modules."""

    __tablename__ = "intelligence_module_statuses"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: str = Column(String(36), ForeignKey("repository_analyses.analysis_id", ondelete="CASCADE"), nullable=False, index=True)
    module_name: str = Column(String(100), nullable=False)
    status: str = Column(String(20), nullable=False)  # queued | running | completed | failed | skipped
    started_at: Optional[datetime] = Column(DateTime, nullable=True)
    finished_at: Optional[datetime] = Column(DateTime, nullable=True)
    duration_seconds: Optional[float] = Column(Float, nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    cache_hit: bool = Column(Boolean, default=False)
    files_processed: int = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('analysis_id', 'module_name', name='uq_analysis_module'),
    )

    analysis = relationship("RepositoryAnalysis")



class ScoreProvenance(Base):
    __tablename__ = "score_provenance"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False)
    dimension = Column(String(50), nullable=False)
    originating_agent = Column(String(100), nullable=False)
    weight = Column(Float, nullable=False)
    raw_score = Column(Integer, nullable=False)
    calibrated_score = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    evaluation = relationship("Evaluation", back_populates="provenance")
    evidence = relationship("ProvenanceEvidence", back_populates="provenance", cascade="all, delete-orphan")


class ProvenanceEvidence(Base):
    __tablename__ = "provenance_evidence"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provenance_id = Column(String(36), ForeignKey("score_provenance.id"), nullable=False)
    rule_id = Column(String(100), nullable=False)
    file_path = Column(String(512), nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False)
    
    provenance = relationship("ScoreProvenance", back_populates="evidence")


class PipelineStageTiming(Base):
    __tablename__ = "pipeline_stage_timings"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False)
    stage = Column(String(100), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    evaluation = relationship("Evaluation", back_populates="stage_timings")


class AgentPromptMetric(Base):
    __tablename__ = "agent_prompt_metrics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    prompt_size_chars = Column(Integer, nullable=False)
    completion_size_chars = Column(Integer, nullable=False)
    latency_seconds = Column(Float, nullable=False)
    
    evaluation = relationship("Evaluation", back_populates="prompt_metrics")


class PipelineDiagnostic(Base):
    __tablename__ = "pipeline_diagnostics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False)
    files_scanned = Column(Integer, default=0)
    ignored_files = Column(Integer, default=0)
    symbols_indexed = Column(Integer, default=0)
    evidence_count = Column(Integer, default=0)
    graph_nodes = Column(Integer, default=0)
    graph_edges = Column(Integer, default=0)
    cache_hit = Column(Boolean, default=False)
    memory_usage_mb = Column(Float, nullable=True)
    repository_digest = Column(String(64), nullable=True)
    evidence_digest = Column(String(64), nullable=True)
    context_digest = Column(String(64), nullable=True)
    prompt_digest = Column(String(64), nullable=True)
    score_digest = Column(String(64), nullable=True)
    narrative_digest = Column(String(64), nullable=True)
    parsing_error = Column(Text, nullable=True)
    evidence_error = Column(Text, nullable=True)
    graphs_error = Column(Text, nullable=True)
    scoring_error = Column(Text, nullable=True)
    cache_error = Column(Text, nullable=True)
    database_error = Column(Text, nullable=True)
    llm_error = Column(Text, nullable=True)
    subsystem_health_json = Column(Text, nullable=True)
    
    evaluation = relationship("Evaluation", back_populates="diagnostics")


class EvaluationAudit(Base):
    __tablename__ = "evaluation_audits"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id = Column(String(36), ForeignKey("evaluations.evaluation_id"), nullable=False)
    stage = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    duration_seconds = Column(Float, nullable=False)
    
    evaluation = relationship("Evaluation", back_populates="audits")


# ── Dependency helper ──────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency that yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and perform automatic schema migrations for missing columns/indexes."""
    # 1. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    # 2. Inspect database for missing columns and run migrations dynamically
    from sqlalchemy import inspect, text
    insp = inspect(engine)

    with engine.begin() as conn:
        for table_name, table_obj in Base.metadata.tables.items():
            try:
                db_cols = {c["name"] for c in insp.get_columns(table_name)}
            except Exception:
                continue

            # A. Remove obsolete columns (e.g. project_id in tables where it's not defined in ORM)
            if "project_id" in db_cols and "project_id" not in table_obj.columns:
                print(f"[MIGRATION] Recreating table '{table_name}' to remove obsolete column 'project_id'.")
                old_table_name = f"{table_name}_old"
                try:
                    # Rename old table
                    conn.execute(text(f"ALTER TABLE {table_name} RENAME TO {old_table_name}"))
                    
                    # Create new table using ORM metadata
                    table_obj.create(bind=conn)
                    
                    # Retrieve columns of the new table
                    new_cols = {c.name for c in table_obj.columns}
                    
                    # Intersection of columns
                    common_cols = list(new_cols.intersection(db_cols))
                    cols_str = ", ".join(f'"{c}"' for c in common_cols)
                    
                    # Copy data
                    conn.execute(text(f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {old_table_name}"))
                    
                    # Drop old table
                    conn.execute(text(f"DROP TABLE {old_table_name}"))
                    print(f"[MIGRATION] Successfully recreated table '{table_name}' to drop column 'project_id'.")
                except Exception as e:
                    print(f"[MIGRATION] Re-creating table '{table_name}' failed: {e}")
                    try:
                        conn.execute(text(f"DROP TABLE {old_table_name}"))
                    except Exception:
                        pass
                
                # Re-fetch database columns after potentially modifying the table
                try:
                    db_cols = {c["name"] for c in insp.get_columns(table_name)}
                except Exception:
                    continue

            # B. Add missing columns
            for col in table_obj.columns:
                if col.name not in db_cols:
                    col_name = col.name
                    # Simplify column type string representation for SQLite ALTER TABLE
                    col_type_str = str(col.type)
                    if "VARCHAR" in col_type_str:
                        col_type_str = "VARCHAR(255)"
                    elif "DATETIME" in col_type_str:
                        col_type_str = "DATETIME"
                    elif "FLOAT" in col_type_str:
                        col_type_str = "FLOAT"
                    elif "INTEGER" in col_type_str:
                        col_type_str = "INTEGER"
                    elif "TEXT" in col_type_str:
                        col_type_str = "TEXT"
                        
                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type_str}"
                    try:
                        conn.execute(text(alter_query))
                        print(f"[MIGRATION] Added column '{col_name}' to table '{table_name}'.")
                    except Exception as e:
                        print(f"[MIGRATION] Failed to add column '{col_name}' to '{table_name}': {e}")
