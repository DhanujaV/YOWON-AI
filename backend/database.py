"""
database.py — SQLAlchemy setup for Project Sentinel.

Tables:
  - projects     : Submitted project metadata
  - evaluations  : Per-agent scores and findings
  - reports      : Final PDF report metadata
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
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import DATABASE_URL


# ── Engine & Session factory ─────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base model ───────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Models ───────────────────────────────────────────────────────────────────

class Project(Base):
    """Represents a user-submitted project pending evaluation."""

    __tablename__ = "projects"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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

    evaluations = relationship("Evaluation", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"


class Evaluation(Base):
    """Stores per-agent evaluation results for a project."""

    __tablename__ = "evaluations"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(String(36), ForeignKey("projects.id"), nullable=False)
    agent_name: str = Column(String(100), nullable=False)  # e.g. "technical", "security"
    score: Optional[float] = Column(Float, nullable=True)  # 0-100
    findings: Optional[str] = Column(Text, nullable=True)  # JSON or prose
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="evaluations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Evaluation agent={self.agent_name} score={self.score}>"


class Report(Base):
    """Tracks generated PDF reports for a project."""

    __tablename__ = "reports"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(String(36), ForeignKey("projects.id"), nullable=False)
    pdf_path: Optional[str] = Column(String(512), nullable=True)
    report_status: str = Column(String(20), default="ready")  # ready | failed
    report_error: Optional[str] = Column(Text, nullable=True)
    overall_score: Optional[float] = Column(Float, nullable=True)
    verdict: Optional[str] = Column(String(20), nullable=True)  # ACCEPT | IMPROVE | REJECT
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="reports")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Report project={self.project_id} verdict={self.verdict}>"


# ── Dependency helper ────────────────────────────────────────────────────────

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
