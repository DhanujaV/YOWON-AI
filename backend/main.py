"""
main.py — FastAPI application for Project Sentinel.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ.setdefault("OLLAMA_API_BASE", "http://localhost:11434")

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from config import CORS_ORIGINS, LOG_LEVEL, UPLOAD_DIR
from database import Evaluation, Project, Report, get_db, init_db
from tools.parser import build_project_context, context_to_text
from tools.vector_store import store_project_context
from crew.crew import run_evaluation
from reports.report_generator import generate_report
from scoring.rubrics import PROJECT_TYPES, normalize_project_type
from progress import (
    PHASE_BUILD_CONTEXT,
    PHASE_EMBEDDINGS,
    PHASE_FETCH_REPO,
    PHASE_REPORT,
    complete,
    fail,
    get_progress,
    init_progress,
    set_current_task,
)
from health_check import run_preflight_checks
from logging_config import setup_logging, timed_operation

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Project Sentinel API",
    description="AI-Powered Deployment Readiness Evaluator",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    _migrate_report_columns()
    _migrate_project_columns()


def _migrate_report_columns() -> None:
    """Add report_status columns to existing SQLite DBs."""
    from sqlalchemy import inspect, text
    from database import engine

    insp = inspect(engine)
    if "reports" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("reports")}
    with engine.begin() as conn:
        if "report_status" not in cols:
            conn.execute(text("ALTER TABLE reports ADD COLUMN report_status VARCHAR(20) DEFAULT 'ready'"))
        if "report_error" not in cols:
            conn.execute(text("ALTER TABLE reports ADD COLUMN report_error TEXT"))


def _migrate_project_columns() -> None:
    """Add project type to existing databases without breaking stored projects."""
    from sqlalchemy import inspect, text
    from database import engine
    if "projects" not in inspect(engine).get_table_names():
        return
    cols = {c["name"] for c in inspect(engine).get_columns("projects")}
    if "project_type" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN project_type VARCHAR(50) NOT NULL DEFAULT 'Hackathon Project'"))


def _save_upload(upload: UploadFile, project_id: str) -> str:
    dest = UPLOAD_DIR / f"{project_id}_{upload.filename}"
    dest.write_bytes(upload.file.read())
    return str(dest)


@app.post("/upload-project", summary="Upload project files and metadata")
async def upload_project(
    name: str = Form(...),
    project_type: str = Form("Hackathon Project"),
    description: str = Form(""),
    github_url: Optional[str] = Form(None),
    demo_video_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    ppt_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    project_id = str(uuid.uuid4())
    pdf_path: Optional[str] = None
    ppt_path: Optional[str] = None

    if project_type not in PROJECT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid project_type. Choose one of: {', '.join(PROJECT_TYPES)}")

    if pdf_file and pdf_file.filename:
        pdf_path = _save_upload(pdf_file, project_id)
    if ppt_file and ppt_file.filename:
        ppt_path = _save_upload(ppt_file, project_id)

    project = Project(
        id=project_id,
        name=name,
        project_type=normalize_project_type(project_type),
        description=description,
        github_url=github_url,
        demo_video_url=demo_video_url,
        pdf_path=pdf_path,
        ppt_path=ppt_path,
        status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return JSONResponse(
        status_code=201,
        content={
            "project_id": project_id,
            "project_type": project.project_type,
            "status": "pending",
            "message": "Project uploaded. Call POST /evaluate/{project_id} to start.",
        },
    )


def _agent_score_map(verdict: dict) -> dict[str, float]:
    scores = verdict.get("agent_scores") or {}
    overall = verdict.get("overall_score", 0)
    return {
        "technical": float(scores.get("technical", 0)),
        "security": float(scores.get("security", 0)),
        "presentation": float(scores.get("presentation", 0)),
        "innovation": float(scores.get("innovation", 0)),
        "risk": float(scores.get("impact", 0)),
        "chief_evaluation": float(overall),
    }


def _run_evaluation_background(project_id: str) -> None:
    from database import SessionLocal

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = "running"
        db.commit()

        init_progress(project_id, reset=True)

        health = run_preflight_checks(require_github=bool(project.github_url))
        if health.warnings:
            for w in health.warnings:
                logger.warning("Preflight: %s", w)
        health.raise_if_critical()

        def _phase(task: str) -> None:
            set_current_task(project_id, task, log=f"[SYS] {task}")

        with timed_operation(logger, "context:build", project_id=project_id):
            _phase(PHASE_BUILD_CONTEXT)
            ctx = build_project_context(
                project_name=project.name,
                project_type=project.project_type,
                description=project.description or "",
                github_url=project.github_url,
                pdf_path=project.pdf_path,
                ppt_path=project.ppt_path,
                on_phase=_phase,
            )
            ctx_text = context_to_text(ctx)

        with timed_operation(logger, "chroma:embed", project_id=project_id):
            _phase(PHASE_EMBEDDINGS)
            store_project_context(project_id, ctx_text, {"project_name": project.name})

        results = run_evaluation(project_id, ctx, ctx_text)

        verdict = results.get("verdict", {})
        if not verdict or verdict.get("overall_score") is None:
            raise RuntimeError("Evaluation produced no verdict — cannot persist results")

        score_map = _agent_score_map(verdict)

        agent_output_map = {
            "technical": results.get("technical", ""),
            "security": results.get("security", ""),
            "presentation": results.get("presentation", ""),
            "innovation": results.get("innovation", ""),
            "risk": results.get("risk", ""),
            "chief_evaluation": results.get("chief_evaluation", ""),
        }

        for agent_name, output_text in agent_output_map.items():
            db.add(
                Evaluation(
                    project_id=project_id,
                    agent_name=agent_name,
                    score=score_map.get(agent_name, 0.0),
                    findings=(output_text or "")[:10000],
                )
            )

        report_id = str(uuid.uuid4())
        pdf_path: Optional[str] = None
        report_status = "ready"
        report_error: Optional[str] = None

        set_current_task(project_id, PHASE_REPORT, log=f"[SYS] {PHASE_REPORT}")
        try:
            pdf_path = generate_report(
                project_name=project.name,
                report_id=report_id,
                evaluation_results=results,
            )
        except Exception as pdf_exc:
            logger.exception("PDF generation failed for %s", project_id)
            report_status = "failed"
            report_error = str(pdf_exc)

        db.add(
            Report(
                id=report_id,
                project_id=project_id,
                pdf_path=pdf_path,
                report_status=report_status,
                report_error=report_error,
                overall_score=verdict.get("overall_score"),
                verdict=verdict.get("verdict") if isinstance(verdict, dict) else str(verdict),
            )
        )

        # Evaluation succeeded even if PDF failed
        project.status = "done"
        db.commit()
        complete(project_id, report_status=report_status, report_error=report_error)

    except Exception as exc:
        logger.exception("Evaluation failed for %s", project_id)
        db.rollback()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
        fail(project_id, str(exc))
    finally:
        db.close()


@app.post("/evaluate/{project_id}", summary="Trigger AI evaluation")
async def trigger_evaluation(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == "running":
        return {"message": "Evaluation already in progress", "status": "running"}

    if project.status != "running":
        init_progress(project_id, reset=True)
        project.status = "running"
        db.commit()

    background_tasks.add_task(_run_evaluation_background, project_id)

    return {
        "project_id": project_id,
        "status": "running",
        "message": "Evaluation started. Stream GET /progress/{project_id}/stream",
    }


@app.get("/status/{project_id}", summary="Check evaluation status")
async def get_status(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = get_progress(project_id)
    report = (
        db.query(Report)
        .filter(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    report_status = report.report_status if report else progress.get("report_status", "pending")
    report_error = report.report_error if report else progress.get("report_error")

    return {
        "project_id": project_id,
        "status": project.status,
        "evaluation_status": "complete" if project.status == "done" else project.status,
        "report_status": report_status,
        "report_error": report_error,
        "name": project.name,
        "project_type": project.project_type,
        "created_at": project.created_at.isoformat(),
        "progress": progress,
    }


@app.get("/progress/{project_id}", summary="Poll evaluation progress")
async def get_evaluation_progress(project_id: str, db: Session = Depends(get_db)):
    progress = get_progress(project_id)
    if progress.get("status") == "unknown":
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        report = (
            db.query(Report)
            .filter(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        return {
            "project_id": project_id,
            "step": 0,
            "total": 8,
            "agent": "coordinator",
            "current_task": "Initializing",
            "status": project.status,
            "evaluation_status": "complete" if project.status == "done" else project.status,
            "report_status": report.report_status if report else "pending",
            "report_error": report.report_error if report else None,
            "elapsed_seconds": 0,
            "completion_percent": 0,
            "logs": [],
            "agent_states": {},
            "events": [],
        }
    return {"project_id": project_id, **progress}


@app.get("/progress/{project_id}/stream", summary="SSE evaluation progress stream")
async def progress_stream(project_id: str):
    async def event_generator():
        last_payload = ""
        while True:
            progress = get_progress(project_id)
            payload = json.dumps({"project_id": project_id, **progress})
            if payload != last_payload:
                last_payload = payload
                yield f"data: {payload}\n\n"
            if progress.get("status") in ("done", "failed"):
                break
            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/report/{project_id}", summary="Get full evaluation report as JSON")
async def get_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "done":
        return JSONResponse(
            status_code=202,
            content={
                "status": project.status,
                "evaluation_status": project.status,
                "report_status": "pending",
                "message": "Evaluation not complete yet",
            },
        )

    report = (
        db.query(Report)
        .filter(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
        .first()
    )

    evaluations = db.query(Evaluation).filter(Evaluation.project_id == project_id).all()
    eval_map = {e.agent_name: {"score": e.score, "findings": e.findings} for e in evaluations}

    verdict_data: dict = {}
    chief_ev = eval_map.get("chief_evaluation")
    if chief_ev and chief_ev.get("findings"):
        from validation.json_utils import extract_json

        parsed = extract_json(chief_ev["findings"], label="report:chief")
        if parsed:
            verdict_data = parsed
        else:
            logger.warning("Could not parse chief findings for project %s", project_id)

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_type": project.project_type,
        "status": project.status,
        "evaluation_status": "complete",
        "report_status": report.report_status if report else "unknown",
        "report_error": report.report_error if report else None,
        "overall_score": report.overall_score if report else verdict_data.get("overall_score"),
        "verdict": report.verdict if report else verdict_data.get("verdict"),
        "report_id": report.id if report else None,
        "evaluations": eval_map,
        "verdict_data": verdict_data,
        "agent_failures": verdict_data.get("agent_failures") if verdict_data else {},
    }


@app.get("/report/{project_id}/pdf", summary="Download the PDF report")
async def download_pdf(project_id: str, db: Session = Depends(get_db)):
    report = (
        db.query(Report)
        .filter(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.report_status == "failed":
        raise HTTPException(
            status_code=503,
            detail=report.report_error or "PDF generation failed",
        )

    if not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available")

    pdf_path = Path(report.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"sentinel_report_{project_id[:8]}.pdf",
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Project Sentinel API",
        "version": "2.2.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", include_in_schema=False)
async def health():
    report = run_preflight_checks()
    return {
        "status": "ok" if report.ok else "degraded",
        "service": "Project Sentinel",
        "version": "2.3.0",
        "ollama_models": report.ollama_models,
        "errors": report.errors,
        "warnings": report.warnings,
    }
