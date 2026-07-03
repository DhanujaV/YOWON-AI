"""
main.py â€” FastAPI application for YOWON AI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware

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
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from config import CORS_ORIGINS, LOG_LEVEL
from database import (
    Project,
    Report,
    Evaluation,
    Repository,
    RepositorySnapshot,
    Technology,
    Dependency,
    RepositoryFile,
    RepositoryFolder,
    AgentEvaluation,
    Evidence,
    Recommendation,
    EvaluationEvent,
    get_db,
    init_db,
)
from intelligence.cache_engine import RepositoryAnalysisCache
from tools.parser import build_project_context, context_to_text
from tools.vector_store import store_project_context
from crew.crew import run_evaluation
from reports.report_generator import PDFGenerationError, generate_report, validate_pdf_file
from scoring.rubrics import PROJECT_TYPES, is_presentation_enabled, normalize_project_type
from utils.ranking_engine import build_ranking_payload, save_evaluation
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
from security import (
    check_rate_limit,
    client_ip,
    enforce_request_size,
    redact_sensitive,
    sanitize_project_name,
    validate_and_save_upload,
    validate_github_url,
    validate_project_id,
)

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)
UPLOAD_PROJECT_TYPES = (*PROJECT_TYPES, "Auto Detect")

app = FastAPI(
    title="YOWON AI API",
    description="Autonomous AI Jury Platform",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            await enforce_request_size(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def safe_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error path=%s client=%s", request.url.path, client_ip(request))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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


@app.post("/upload-project", summary="Upload project files and metadata")
async def upload_project(
    request: Request,
    name: str = Form(...),
    project_type: str = Form("Hackathon Project"),
    description: str = Form(""),
    github_url: Optional[str] = Form(None),
    demo_video_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    ppt_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    check_rate_limit("upload", client_ip(request))
    project_id = str(uuid.uuid4())
    pdf_path: Optional[str] = None
    ppt_path: Optional[str] = None
    safe_name = sanitize_project_name(name)
    safe_github_url = validate_github_url(github_url)

    if project_type not in UPLOAD_PROJECT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid project_type. Choose one of: {', '.join(UPLOAD_PROJECT_TYPES)}")

    try:
        if pdf_file and pdf_file.filename:
            pdf_path = await validate_and_save_upload(pdf_file, project_id, "pdf")
        if ppt_file and ppt_file.filename:
            ppt_path = await validate_and_save_upload(ppt_file, project_id, "ppt")
    except HTTPException as exc:
        logger.warning(
            "Rejected upload client=%s project_id=%s reason=%s",
            client_ip(request),
            project_id,
            redact_sensitive(str(exc.detail)),
        )
        raise

    project = Project(
        id=project_id,
        name=safe_name,
        project_type="Auto Detect" if project_type == "Auto Detect" else normalize_project_type(project_type),
        description="",
        github_url=safe_github_url,
        demo_video_url=None,
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
    score_map = {
        "forge": float(scores.get("technical", 0)),
        "technical": float(scores.get("technical", 0)),
        "sentinel": float(scores.get("security", 0)),
        "security": float(scores.get("security", 0)),
        "visionary": float(scores.get("innovation", 0)),
        "innovation": float(scores.get("innovation", 0)),
        "guardian": float(scores.get("impact", 0)),
        "risk": float(scores.get("impact", 0)),
        "yowon_prime": float(overall),
        "chief_evaluation": float(overall),
    }
    if is_presentation_enabled(verdict.get("submitted_project_type") or verdict.get("project_type")) and "presentation" in scores:
        score_map["showcase"] = float(scores.get("presentation", 0))
        score_map["presentation"] = float(scores.get("presentation", 0))
    return score_map


INTERNAL_VERDICT_FIELDS = {
    "raw_agent_scores",
    "calibrated_agent_scores",
    "agent_calibration_reasons",
    "calibration_adjustments",
    "raw_weighted_score",
}


def _public_verdict_data(verdict: dict) -> dict:
    """Strip backend-only scoring diagnostics from user-facing responses."""
    if not isinstance(verdict, dict):
        return {}
    public = {k: v for k, v in verdict.items() if k not in INTERNAL_VERDICT_FIELDS}
    if not is_presentation_enabled(public.get("submitted_project_type") or public.get("project_type")):
        for score_key in ("agent_scores",):
            scores = public.get(score_key)
            if isinstance(scores, dict):
                public[score_key] = {
                    key: value for key, value in scores.items()
                    if key not in {"presentation", "showcase", "ppt"}
                }
        weights = public.get("scoring_weights")
        if isinstance(weights, dict):
            public["scoring_weights"] = {
                key: value for key, value in weights.items() if key != "presentation"
            }
        public["penalties"] = [
            item for item in (public.get("penalties") or [])
            if not (isinstance(item, dict) and item.get("dimension") == "presentation")
        ]
    return public


def _chief_public_findings(verdict: dict) -> str:
    public = _public_verdict_data(verdict)
    lines = [
        "YOWON Prime Verdict",
        f"Status: {public.get('status', 'COMPLETE')}",
        f"Overall Score: {public.get('overall_score', 0)}/100",
        f"Verdict: {public.get('verdict', 'REJECT')}",
        f"Risk Level: {public.get('risk_level', 'UNKNOWN')}",
        f"Score Band: {public.get('score_band', 'Unknown')}",
        f"Confidence: {public.get('confidence', 0)}/100",
        "",
        "Executive Summary:",
        public.get("executive_summary") or public.get("final_reason") or "No executive summary available.",
    ]
    if public.get("blocking_issues"):
        lines.extend(["", "Blocking Issues:"])
        lines.extend(f"- {item}" for item in public["blocking_issues"])
    if public.get("recommended_fixes"):
        lines.extend(["", "Recommended Fixes:"])
        lines.extend(f"- {item}" for item in public["recommended_fixes"])
    return "\n".join(lines)


def extract_normalized_dependencies_and_technologies(dep_files: dict[str, str]) -> tuple[list[dict], list[dict]]:
    dependencies = []
    technologies = []
    
    seen_deps = set()
    seen_techs = set()
    
    for filepath, content in dep_files.items():
        fname = filepath.lower().split("/")[-1]
        if fname == "package.json":
            try:
                data = json.loads(content)
                deps_dict = data.get("dependencies", {})
                dev_deps_dict = data.get("devDependencies", {})
                for name, ver in {**deps_dict, **dev_deps_dict}.items():
                    clean_ver = str(ver).strip("^~*").split()[0] if ver else None
                    if name not in seen_deps:
                        dependencies.append({"name": name, "version": clean_ver, "type": "npm"})
                        seen_deps.add(name)
                for tech_name in ["react", "vue", "angular", "next", "nuxt", "svelte", "express", "tailwindcss", "typescript"]:
                    if tech_name in deps_dict or tech_name in dev_deps_dict:
                        if tech_name not in seen_techs:
                            technologies.append({"name": tech_name.capitalize(), "version": None})
                            seen_techs.add(tech_name)
            except Exception:
                pass
        elif fname in ("requirements.txt", "requirements-dev.txt"):
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "-", "git+", "http")):
                    continue
                import re
                parts = re.split(r"==|>=|<=|~=", line)
                dep_name = parts[0].strip().split("[")[0].strip()
                dep_ver = parts[1].strip() if len(parts) > 1 else None
                if dep_name and dep_name not in seen_deps:
                    dependencies.append({"name": dep_name, "version": dep_ver, "type": "python"})
                    seen_deps.add(dep_name)
                for tech_name in ["django", "flask", "fastapi", "numpy", "pandas", "tensorflow", "torch", "scikit-learn"]:
                    if tech_name == dep_name.lower():
                        if tech_name not in seen_techs:
                            technologies.append({"name": tech_name.capitalize(), "version": dep_ver})
                            seen_techs.add(tech_name)
        elif fname == "go.mod":
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("require"):
                    continue
                import re
                match = re.match(r"^([a-zA-Z0-9.\-_/]+)\s+([a-zA-Z0-9.\-_]+)", line)
                if match:
                    name, ver = match.groups()
                    if name not in seen_deps:
                        dependencies.append({"name": name, "version": ver, "type": "go"})
                        seen_deps.add(name)
        elif fname == "cargo.toml":
            in_deps = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("[dependencies]") or line.startswith("[dev-dependencies]"):
                    in_deps = True
                    continue
                elif line.startswith("[") and in_deps:
                    in_deps = False
                if in_deps and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    ver = parts[1].strip().strip('"\'{} ')
                    if name not in seen_deps:
                        dependencies.append({"name": name, "version": ver, "type": "cargo"})
                        seen_deps.add(name)
                        
    return dependencies, technologies


def parse_evidence_from_findings(finding_str: str, repo_files: list[str]) -> tuple[Optional[str], Optional[int], Optional[int]]:
    import re
    # Check for path:line_start-line_end or path:line_start
    match = re.search(r"([\w.\-/]+\.\w+):(\d+)(?:-(\d+))?", finding_str)
    if match:
        filepath = match.group(1)
        line_start = int(match.group(2))
        line_end = int(match.group(3)) if match.group(3) else line_start
        return filepath, line_start, line_end
    
    # Check if any repository file is mentioned in the text
    for file_path in repo_files:
        filename = file_path.split("/")[-1]
        if filename in finding_str:
            return file_path, 1, 10
            
    return None, None, None


def _run_evaluation_background(project_id: str) -> None:
    from database import SessionLocal
    import time
    from datetime import datetime
    import json
    import re
    import hashlib
    import os
    from config import MODEL_NAME

    db: Session = SessionLocal()
    start_time = time.perf_counter()
    evaluation_id = str(uuid.uuid4())

    def add_event(name: str, status: str = "completed", duration: float = 0, metadata: dict = None):
        evt = EvaluationEvent(
            id=str(uuid.uuid4()),
            evaluation_id=evaluation_id,
            event_name=name,
            timestamp=datetime.utcnow(),
            duration=duration,
            event_metadata=json.dumps(metadata) if metadata else None,
            status=status
        )
        db.add(evt)
        db.commit()

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

        # --- Repository & Snapshot Setup ---
        snapshot_id = None
        repo_files_list = []
        
        t_phase = time.perf_counter()
        _phase(PHASE_BUILD_CONTEXT)
        
        ctx = build_project_context(
            project_name=project.name,
            project_type=project.project_type,
            description="",
            github_url=project.github_url,
            pdf_path=project.pdf_path,
            ppt_path=project.ppt_path,
            on_phase=_phase,
        )
        ctx_text = context_to_text(ctx)
        
        duration_ctx = time.perf_counter() - t_phase
        
        # Create Evaluation run first so we can link events
        main_eval = Evaluation(
            evaluation_id=evaluation_id,
            project_id=project_id,
            timestamp=datetime.utcnow(),
            evaluation_status="Running",
            llm_model=MODEL_NAME,
            embedding_model=MODEL_NAME,
            evaluation_version="1.0.0",
            prompt_version="1.0.0",
            rubric_version="1.0.0"
        )
        db.add(main_eval)
        db.commit()
        
        add_event("Repository Indexed", duration=duration_ctx)

        if project.github_url and ctx.get("github") and not ctx["github"].get("error"):
            gh_data = ctx["github"]
            
            # 1. Logical Repository
            repo = db.query(Repository).filter(Repository.github_url == project.github_url).first()
            if not repo:
                repo = Repository(
                    repository_id=str(uuid.uuid4()),
                    project_id=project_id,
                    github_repository_id=gh_data.get("github_repository_id"),
                    github_url=project.github_url,
                    owner=gh_data.get("owner"),
                    repository_name=gh_data.get("repository_name"),
                    default_branch=gh_data.get("default_branch"),
                    visibility=gh_data.get("visibility", "public"),
                    stars=gh_data.get("stars", 0),
                    forks=gh_data.get("forks", 0),
                    open_issues=gh_data.get("open_issues", 0),
                    license=gh_data.get("license"),
                    topics=json.dumps(gh_data.get("topics", [])),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(repo)
                db.commit()
            
            # 2. Snapshot
            snapshot_id = str(uuid.uuid4())
            repo_files_list = gh_data.get("repository_files", [])
            stats = gh_data.get("repository_statistics", {})
            folder_structure = gh_data.get("folder_structure", [])
            
            dep_files = gh_data.get("dependencies", {})
            dependencies_parsed, technologies_parsed = extract_normalized_dependencies_and_technologies(dep_files)
            
            last_commit_dt = None
            if gh_data.get("last_commit_timestamp"):
                try:
                    last_commit_dt = datetime.fromisoformat(gh_data["last_commit_timestamp"])
                except Exception:
                    pass
            
            # Link previous snapshot if exists for timeline tracking
            prev_snapshot = db.query(RepositorySnapshot).filter(
                RepositorySnapshot.repository_id == repo.repository_id
            ).order_by(RepositorySnapshot.snapshot_timestamp.desc()).first()
            prev_snapshot_id = prev_snapshot.snapshot_id if prev_snapshot else None
            
            snapshot = RepositorySnapshot(
                snapshot_id=snapshot_id,
                repository_id=repo.repository_id,
                commit_sha=gh_data.get("commit_sha", "unknown-commit"),
                tree_sha=gh_data.get("tree_sha"),
                branch=gh_data.get("branch", "main"),
                readme_snapshot=gh_data.get("readme"),
                repository_statistics=json.dumps(stats),
                folder_structure=json.dumps(folder_structure),
                technology_summary=json.dumps(technologies_parsed),
                dependency_summary=json.dumps(dependencies_parsed),
                architecture_summary=ctx.get("architecture", {}).get("summary"),
                last_commit_timestamp=last_commit_dt,
                snapshot_timestamp=datetime.utcnow(),
                previous_snapshot_id=prev_snapshot_id
            )
            db.add(snapshot)
            db.commit()
            
            main_eval.repository_snapshot_id = snapshot_id
            db.commit()
            
            # Save Technologies
            for tech in technologies_parsed:
                db.add(Technology(
                    id=str(uuid.uuid4()),
                    repository_id=repo.repository_id,
                    name=tech["name"],
                    version=tech["version"]
                ))
            
            # Save Dependencies
            for dep in dependencies_parsed:
                db.add(Dependency(
                    id=str(uuid.uuid4()),
                    repository_id=repo.repository_id,
                    name=dep["name"],
                    version=dep["version"],
                    type=dep["type"]
                ))
            
            # Save Repository Files
            for filepath in repo_files_list[:100]:
                ext = filepath.split(".")[-1] if "." in filepath else None
                db.add(RepositoryFile(
                    id=str(uuid.uuid4()),
                    snapshot_id=snapshot_id,
                    path=filepath,
                    size_bytes=0,
                    language=ext
                ))
                
            # Save Repository Folders
            unique_folders = {filepath.rsplit("/", 1)[0] for filepath in repo_files_list if "/" in filepath}
            for folderpath in list(unique_folders)[:50]:
                db.add(RepositoryFolder(
                    id=str(uuid.uuid4()),
                    snapshot_id=snapshot_id,
                    path=folderpath
                ))
                
            db.commit()
            
            # Run Repository Intelligence static analysis
            try:
                from intelligence.intelligence_service import run_repository_intelligence
                run_repository_intelligence(db, main_eval, snapshot_id)
            except Exception as intel_exc:
                logger.exception("[SYS] Repository Intelligence static analysis failed: %s", intel_exc)

        # Architecture Parsing Event
        t_phase = time.perf_counter()
        _phase(PHASE_EMBEDDINGS)
        store_project_context(project_id, ctx_text, {"project_name": project.name})
        add_event("Architecture Parsed", duration=time.perf_counter() - t_phase)

        # Specialist Runs Events & Evaluation
        t_eval_start = time.perf_counter()
        results = run_evaluation(project_id, ctx, ctx_text)
        
        # Log specialist runs events
        add_event("Security Completed", duration=results.get("evaluation_duration_sec", 0) / 4)
        add_event("Forge Completed", duration=results.get("evaluation_duration_sec", 0) / 4)
        add_event("Guardian Completed", duration=results.get("evaluation_duration_sec", 0) / 4)
        add_event("Visionary Completed", duration=results.get("evaluation_duration_sec", 0) / 4)
        add_event("Insight Completed", duration=results.get("evaluation_duration_sec", 0) / 10)

        verdict = results.get("verdict", {})
        if not verdict or verdict.get("overall_score") is None:
            raise RuntimeError("Evaluation produced no verdict — cannot persist results")

        try:
            score_for_ranking = verdict.get("overall_score", 0)
            type_for_ranking = verdict.get("project_type") or project.project_type
            save_evaluation(project.name, type_for_ranking, score_for_ranking)
            verdict["ranking"] = build_ranking_payload(score_for_ranking, type_for_ranking)
        except Exception:
            logger.exception("Ranking update failed for %s", project_id)
            verdict["ranking"] = {
                "global_percentile": None,
                "global_rank": "Insufficient Data",
                "category_percentile": None,
                "category_rank": "Insufficient Data",
                "projects_compared": 0,
                "category_projects_compared": 0,
            }
        results["verdict"] = verdict
        results["chief_evaluation"] = json.dumps(verdict, indent=2)

        score_map = _agent_score_map(verdict)
        
        if results.get("rejection_report"):
            agent_output_map = {"yowon_prime": results.get("chief_evaluation", "")}
        else:
            agent_output_map = {
                "forge": results.get("technical", ""),
                "sentinel": results.get("security", ""),
                "visionary": results.get("innovation", ""),
                "guardian": results.get("risk", ""),
                "yowon_prime": results.get("chief_evaluation", ""),
            }
            if is_presentation_enabled(verdict.get("submitted_project_type") or project.project_type):
                agent_output_map["showcase"] = results.get("presentation", "")

        for agent_name, output_text in agent_output_map.items():
            db.add(
                AgentEvaluation(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    agent_name=agent_name,
                    score=score_map.get(agent_name, 0.0),
                    confidence=0.85,
                    execution_time=results.get("evaluation_duration_sec", 0) / len(agent_output_map),
                    summary=(output_text or "")[:10000],
                    status="completed"
                )
            )
        db.commit()

        # Save Evidence
        evidence_rows = []
        if "technical" in results and hasattr(results["technical"], "strengths"):
            tech_report = results["technical"]
            for strength in getattr(tech_report, "strengths", []):
                evidence_rows.append(Evidence(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    category="IMPLEMENTATION",
                    finding=f"Strength: {strength}",
                    confidence=getattr(tech_report, "confidence", 0.8),
                    severity="INFO"
                ))
            for weakness in getattr(tech_report, "weaknesses", []):
                filepath, l_start, l_end = parse_evidence_from_findings(weakness, repo_files_list)
                evidence_rows.append(Evidence(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    category="IMPLEMENTATION",
                    finding=weakness,
                    file_path=filepath,
                    line_start=l_start,
                    line_end=l_end,
                    confidence=getattr(tech_report, "confidence", 0.8),
                    severity="MEDIUM"
                ))
                
        if "security" in results and hasattr(results["security"], "critical_findings"):
            sec_report = results["security"]
            for finding in getattr(sec_report, "critical_findings", []):
                filepath, l_start, l_end = parse_evidence_from_findings(finding, repo_files_list)
                severity_val = getattr(sec_report, "risk_level", "HIGH")
                evidence_rows.append(Evidence(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    category="SECURITY",
                    finding=finding,
                    file_path=filepath,
                    line_start=l_start,
                    line_end=l_end,
                    confidence=getattr(sec_report, "confidence", 0.8),
                    severity=severity_val
                ))
                
        for ev in evidence_rows:
            db.add(ev)
        db.commit()

        # Save Recommendations
        for ev in evidence_rows:
            if ev.severity in ["MEDIUM", "HIGH", "CRITICAL"]:
                db.add(Recommendation(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    evidence_id=ev.id,
                    priority="HIGH" if ev.severity in ["HIGH", "CRITICAL"] else "MEDIUM",
                    category=ev.category,
                    recommendation=f"Resolve the issue in {ev.file_path or 'codebase'}: {ev.finding}",
                    expected_score_gain=5.0 if ev.severity == "CRITICAL" else 3.0,
                    estimated_effort="1-2 hours",
                    status="Pending"
                ))
        db.commit()

        add_event("Prime Completed", duration=time.perf_counter() - t_eval_start)

        # Report Generation
        t_report_start = time.perf_counter()
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
            validate_pdf_file(pdf_path)
        except Exception as pdf_exc:
            logger.exception("PDF generation failed for %s", project_id)
            report_status = "failed"
            report_error = str(pdf_exc)
            pdf_path = None

        duration_report = time.perf_counter() - t_report_start

        file_size = 0
        checksum_val = None
        if pdf_path and os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            try:
                with open(pdf_path, "rb") as f:
                    checksum_val = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                pass

        db.add(
            Report(
                report_id=report_id,
                evaluation_id=evaluation_id,
                report_type="PDF",
                file_path=pdf_path,
                file_size=file_size,
                checksum=checksum_val,
                generated_at=datetime.utcnow(),
                generation_time=duration_report,
                version="1.0.0"
            )
        )
        db.commit()
        
        add_event("Report Generated", duration=duration_report)

        # Update main evaluation stats
        main_eval.overall_score = verdict.get("overall_score")
        main_eval.verdict = verdict.get("verdict") if isinstance(verdict, dict) else str(verdict)
        main_eval.confidence = verdict.get("confidence", 0) / 100.0 if verdict.get("confidence") else None
        main_eval.evaluation_duration = time.perf_counter() - start_time
        main_eval.evaluation_status = "Completed"
        
        project.status = "done"
        db.commit()
        
        complete(project_id, report_status=report_status, report_error=report_error)

    except Exception as exc:
        logger.exception("Evaluation failed for %s", project_id)
        db.rollback()
        
        failed_eval = db.query(Evaluation).filter(Evaluation.evaluation_id == evaluation_id).first()
        if failed_eval:
            failed_eval.evaluation_status = "Failed"
            db.commit()
            
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
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    validate_project_id(project_id)
    check_rate_limit("evaluate", client_ip(request))
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
    validate_project_id(project_id)
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
    validate_project_id(project_id)
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
    validate_project_id(project_id)
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
    validate_project_id(project_id)
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

    latest_eval = (
        db.query(Evaluation)
        .filter(Evaluation.project_id == project_id, Evaluation.evaluation_status == "Completed")
        .order_by(Evaluation.timestamp.desc())
        .first()
    )
    if latest_eval:
        eval_map = {
            ae.agent_name: {"score": ae.score, "findings": ae.summary}
            for ae in latest_eval.agent_evaluations
        }
    else:
        evals = db.query(AgentEvaluation).filter(AgentEvaluation.evaluation.has(project_id=project_id)).all()
        eval_map = {e.agent_name: {"score": e.score, "findings": e.summary} for e in evals}

    verdict_data: dict = {}
    chief_ev = eval_map.get("yowon_prime") or eval_map.get("chief_evaluation")
    if chief_ev and chief_ev.get("findings"):
        parsed = extract_json(chief_ev["findings"], label="report:chief")
        if parsed:
            verdict_data = parsed
        else:
            logger.warning("Could not parse chief findings for project %s", project_id)
    public_verdict = _public_verdict_data(verdict_data)
    if public_verdict and "ranking" not in public_verdict:
        score = public_verdict.get("overall_score", report.overall_score if report else None)
        if score is not None:
            public_verdict["ranking"] = build_ranking_payload(
                score,
                public_verdict.get("project_type") or project.project_type,
            )
    if "yowon_prime" in eval_map:
        eval_map["yowon_prime"]["findings"] = _chief_public_findings(public_verdict)
    elif "chief_evaluation" in eval_map:
        eval_map["chief_evaluation"]["findings"] = _chief_public_findings(public_verdict)

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
        "evaluation_id": latest_eval.evaluation_id if latest_eval else None,
        "evaluations": eval_map,
        "verdict_data": public_verdict,
        "agent_failures": public_verdict.get("agent_failures") if public_verdict else {},
    }


@app.get("/report/{project_id}/pdf", summary="Download the PDF report")
async def download_pdf(project_id: str, db: Session = Depends(get_db)):
    validate_project_id(project_id)
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
    try:
        size = validate_pdf_file(pdf_path)
        logger.info("[PDF] Validation passed report_id=%s bytes=%d", report.id, size)
    except PDFGenerationError as exc:
        logger.error("[PDF] Validation failed report_id=%s error=%s", report.id, redact_sensitive(str(exc)))
        raise HTTPException(status_code=503, detail="PDF file is invalid") from exc

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"yowon_report_{project_id[:8]}.pdf",
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "YOWON AI API",
        "version": "2.2.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", include_in_schema=False)
async def health():
    report = run_preflight_checks()
    return {
        "status": "ok" if report.ok else "degraded",
        "service": "YOWON AI",
        "version": "2.3.0",
        "ollama_models": report.ollama_models,
        "errors": report.errors,
        "warnings": report.warnings,
    }


# ── New Persistent Project & Evaluation APIs ──────────────────────────────────

@app.get("/projects", summary="List all projects with pagination, sorting, and search")
async def list_projects(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(Project)
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%") | Project.description.ilike(f"%{search}%"))
    
    sort_col = getattr(Project, sort_by, Project.created_at)
    if order.lower() == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())
        
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "project_type": p.project_type,
                "description": p.description,
                "github_url": p.github_url,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in items
        ]
    }


@app.get("/projects/{id}", summary="Get specific project and repository metadata")
async def get_project_by_id(id: str, db: Session = Depends(get_db)):
    validate_project_id(id)
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {
        "id": project.id,
        "name": project.name,
        "project_type": project.project_type,
        "description": project.description,
        "github_url": project.github_url,
        "demo_video_url": project.demo_video_url,
        "pdf_path": project.pdf_path,
        "ppt_path": project.ppt_path,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "repositories": [
            {
                "repository_id": r.repository_id,
                "github_repository_id": r.github_repository_id,
                "github_url": r.github_url,
                "owner": r.owner,
                "repository_name": r.repository_name,
                "default_branch": r.default_branch,
                "visibility": r.visibility,
                "stars": r.stars,
                "forks": r.forks,
                "open_issues": r.open_issues,
                "license": r.license
            }
            for r in project.repositories
        ]
    }


@app.get("/projects/{id}/history", summary="Get evaluation runs history list for a project")
async def get_project_evaluation_history(id: str, db: Session = Depends(get_db)):
    validate_project_id(id)
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    evals = db.query(Evaluation).filter(Evaluation.project_id == id).order_by(Evaluation.timestamp.desc()).all()
    return [
        {
            "evaluation_id": e.evaluation_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "evaluation_duration": e.evaluation_duration,
            "overall_score": e.overall_score,
            "verdict": e.verdict,
            "confidence": e.confidence,
            "evaluation_status": e.evaluation_status,
            "commit_sha": e.snapshot.commit_sha if e.snapshot else None,
            "branch": e.snapshot.branch if e.snapshot else None
        }
        for e in evals
    ]


@app.get("/evaluations/{id}", summary="Get detailed evaluation run results, snapshot, evidence, recommendations, and events")
async def get_evaluation_by_id(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
        
    reports_list = []
    for r in evaluation.reports:
        reports_list.append({
            "report_id": r.report_id,
            "report_type": r.report_type,
            "file_path": r.file_path,
            "file_size": r.file_size,
            "checksum": r.checksum,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "generation_time": r.generation_time,
            "version": r.version
        })
        
    return {
        "evaluation_id": evaluation.evaluation_id,
        "project_id": evaluation.project_id,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "evaluation_duration": evaluation.evaluation_duration,
        "overall_score": evaluation.overall_score,
        "verdict": evaluation.verdict,
        "confidence": evaluation.confidence,
        "evaluation_status": evaluation.evaluation_status,
        "llm_model": evaluation.llm_model,
        "embedding_model": evaluation.embedding_model,
        "evaluation_version": evaluation.evaluation_version,
        "prompt_version": evaluation.prompt_version,
        "rubric_version": evaluation.rubric_version,
        "snapshot": {
            "snapshot_id": evaluation.snapshot.snapshot_id,
            "commit_sha": evaluation.snapshot.commit_sha,
            "tree_sha": evaluation.snapshot.tree_sha,
            "branch": evaluation.snapshot.branch,
            "readme_snapshot": evaluation.snapshot.readme_snapshot[:500] if evaluation.snapshot.readme_snapshot else None,
            "repository_statistics": json.loads(evaluation.snapshot.repository_statistics) if evaluation.snapshot.repository_statistics else {},
            "folder_structure": json.loads(evaluation.snapshot.folder_structure) if evaluation.snapshot.folder_structure else [],
            "technology_summary": json.loads(evaluation.snapshot.technology_summary) if evaluation.snapshot.technology_summary else [],
            "dependency_summary": json.loads(evaluation.snapshot.dependency_summary) if evaluation.snapshot.dependency_summary else [],
            "architecture_summary": evaluation.snapshot.architecture_summary
        } if evaluation.snapshot else None,
        "agent_evaluations": [
            {
                "agent_name": ae.agent_name,
                "score": ae.score,
                "confidence": ae.confidence,
                "execution_time": ae.execution_time,
                "summary": ae.summary,
                "status": ae.status
            }
            for ae in evaluation.agent_evaluations
        ],
        "evidence": [
            {
                "id": ev.id,
                "category": ev.category,
                "finding": ev.finding,
                "file_path": ev.file_path,
                "line_start": ev.line_start,
                "line_end": ev.line_end,
                "confidence": ev.confidence,
                "severity": ev.severity
            }
            for ev in evaluation.evidences
        ],
        "recommendations": [
            {
                "id": rec.id,
                "priority": rec.priority,
                "category": rec.category,
                "recommendation": rec.recommendation,
                "expected_score_gain": rec.expected_score_gain,
                "estimated_effort": rec.estimated_effort,
                "status": rec.status,
                "evidence_id": rec.evidence_id
            }
            for rec in evaluation.recommendations
        ],
        "reports": reports_list,
        "events": [
            {
                "event_name": evt.event_name,
                "timestamp": evt.timestamp.isoformat() if evt.timestamp else None,
                "duration": evt.duration,
                "status": evt.status
            }
            for evt in evaluation.events
        ]
    }


@app.delete("/evaluations/{id}", summary="Delete specific evaluation run")
async def delete_evaluation(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
        
    db.delete(evaluation)
    db.commit()
    return {"message": f"Evaluation {id} deleted successfully"}


@app.get("/evaluations/{id}/compare/{other}", summary="Compare two evaluation runs and return structural differences")
async def compare_evaluations(id: str, other: str, db: Session = Depends(get_db)):
    eval_new = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    eval_old = db.query(Evaluation).filter(Evaluation.evaluation_id == other).first()
    if not eval_new or not eval_old:
        raise HTTPException(status_code=404, detail="One or both evaluations not found")
        
    score_diff = (eval_new.overall_score or 0.0) - (eval_old.overall_score or 0.0)
    verdict_changed = eval_new.verdict != eval_old.verdict
    
    agent_scores_new = {ae.agent_name: ae.score or 0.0 for ae in eval_new.agent_evaluations}
    agent_scores_old = {ae.agent_name: ae.score or 0.0 for ae in eval_old.agent_evaluations}
    agent_diffs = {}
    for agent in set(agent_scores_new.keys()) | set(agent_scores_old.keys()):
        agent_diffs[agent] = agent_scores_new.get(agent, 0.0) - agent_scores_old.get(agent, 0.0)
        
    tech_new = set()
    tech_old = set()
    if eval_new.snapshot and eval_new.snapshot.technology_summary:
        try:
            tech_new = {t["name"] for t in json.loads(eval_new.snapshot.technology_summary)}
        except Exception:
            pass
    if eval_old.snapshot and eval_old.snapshot.technology_summary:
        try:
            tech_old = {t["name"] for t in json.loads(eval_old.snapshot.technology_summary)}
        except Exception:
            pass
            
    dep_new = set()
    dep_old = set()
    if eval_new.snapshot and eval_new.snapshot.dependency_summary:
        try:
            dep_new = {d["name"] for d in json.loads(eval_new.snapshot.dependency_summary)}
        except Exception:
            pass
    if eval_old.snapshot and eval_old.snapshot.dependency_summary:
        try:
            dep_old = {d["name"] for d in json.loads(eval_old.snapshot.dependency_summary)}
        except Exception:
            pass
            
    added_techs = list(tech_new - tech_old)
    removed_techs = list(tech_old - tech_new)
    added_deps = list(dep_new - dep_old)
    removed_deps = list(dep_old - dep_new)
    
    stats_new = {}
    stats_old = {}
    if eval_new.snapshot and eval_new.snapshot.repository_statistics:
        try:
            stats_new = json.loads(eval_new.snapshot.repository_statistics)
        except Exception:
            pass
    if eval_old.snapshot and eval_old.snapshot.repository_statistics:
        try:
            stats_old = json.loads(eval_old.snapshot.repository_statistics)
        except Exception:
            pass
            
    completeness_new = stats_new.get("repository_completeness_score", 0.0)
    completeness_old = stats_old.get("repository_completeness_score", 0.0)
    completeness_diff = completeness_new - completeness_old
    
    sec_new = [e.finding for e in eval_new.evidences if e.category == "SECURITY"]
    sec_old = [e.finding for e in eval_old.evidences if e.category == "SECURITY"]
    added_risks = [f for f in sec_new if f not in sec_old]
    resolved_risks = [f for f in sec_old if f not in sec_new]
    
    rec_new = [r.recommendation for r in eval_new.recommendations]
    rec_old = [r.recommendation for r in eval_old.recommendations]
    added_recs = [r for r in rec_new if r not in rec_old]
    resolved_recs = [r for r in rec_old if r not in rec_new]
    
    return {
        "evaluation_id_new": id,
        "evaluation_id_old": other,
        "score_difference": score_diff,
        "verdict_changed": verdict_changed,
        "verdict_new": eval_new.verdict,
        "verdict_old": eval_old.verdict,
        "agent_scores_difference": agent_diffs,
        "technologies": {
            "added": added_techs,
            "removed": removed_techs
        },
        "dependencies": {
            "added": added_deps,
            "removed": removed_deps
        },
        "completeness_score_difference": completeness_diff,
        "risks": {
            "added": added_risks,
            "resolved": resolved_risks
        },
        "recommendations": {
            "added": added_recs,
            "resolved": resolved_recs
        }
    }


# ── Repository Intelligence APIs ──────────────────────────────────────────────

@app.get("/evaluations/{id}/repository-tree")
async def get_evaluation_tree(id: str, path: Optional[str] = None, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    
    commit_sha = evaluation.snapshot.commit_sha
    tree = RepositoryAnalysisCache.get_artifact(commit_sha, "repository_tree")
    if not tree:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        tree = intel_data["repository_tree"]
    
    if path:
        parts = path.strip("/").split("/")
        curr = tree
        for part in parts:
            found = False
            for child in curr:
                if child["name"] == part and child["type"] == "dir":
                    curr = child.get("children", []) or []
                    found = True
                    break
            if not found:
                return []
        # Strip grandchildren
        for node in curr:
            if "children" in node:
                node["children"] = None
        return curr
    
    # Strip grandchildren for root
    for node in tree:
        if "children" in node:
            node["children"] = None
    return tree


@app.get("/evaluations/{id}/architecture")
async def get_evaluation_architecture(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    graph = RepositoryAnalysisCache.get_artifact(commit_sha, "architecture_graph")
    if not graph:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        graph = intel_data["architecture_graph"]
    return graph


@app.get("/evaluations/{id}/technology-graph")
async def get_evaluation_technology_graph(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    graph = RepositoryAnalysisCache.get_artifact(commit_sha, "technology_graph")
    if not graph:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        graph = intel_data["technology_graph"]
    return graph


@app.get("/evaluations/{id}/dependency-graph")
async def get_evaluation_dependency_graph(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    graph = RepositoryAnalysisCache.get_artifact(commit_sha, "dependency_graph")
    if not graph:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        graph = intel_data["dependency_graph"]
    return graph


@app.get("/evaluations/{id}/call-graph")
async def get_evaluation_call_graph(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    graph = RepositoryAnalysisCache.get_artifact(commit_sha, "call_graph")
    if not graph:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        graph = intel_data["call_graph"]
    return graph


@app.get("/evaluations/{id}/metrics")
async def get_evaluation_metrics(id: str, page: int = 1, size: int = 50, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    metrics = RepositoryAnalysisCache.get_artifact(commit_sha, "metrics")
    if not metrics:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        metrics = intel_data["metrics"]
    
    all_keys = list(metrics.keys())
    start = (page - 1) * size
    end = start + size
    paginated_keys = all_keys[start:end]
    
    return {
        "total": len(all_keys),
        "page": page,
        "size": size,
        "metrics": {k: metrics[k] for k in paginated_keys}
    }


@app.get("/evaluations/{id}/health")
async def get_evaluation_health(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    health = RepositoryAnalysisCache.get_artifact(commit_sha, "health")
    if not health:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        health = intel_data["health"]
    return health


@app.get("/evaluations/{id}/heatmap")
async def get_evaluation_heatmap(id: str, metric: str = "risk", db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    metrics = RepositoryAnalysisCache.get_artifact(commit_sha, "metrics")
    if not metrics:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        metrics = intel_data["metrics"]
    
    heatmap_data = []
    for path, data in metrics.items():
        val = 0
        if metric == "risk":
            val = data.get("risk", 10)
        elif metric == "importance":
            val = data.get("importance", 10)
        elif metric == "coverage":
            val = data.get("coverage", 0)
        elif metric == "complexity":
            val = data.get("complexity", {}).get("cyclomatic_complexity", 1)
        
        heatmap_data.append({
            "name": path.split("/")[-1],
            "path": path,
            "value": data.get("size_bytes", 100),
            "metric_value": val
        })
    return heatmap_data


@app.get("/evaluations/{id}/evidence")
async def get_evaluation_evidence(id: str, page: int = 1, size: int = 50, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    evidence = RepositoryAnalysisCache.get_artifact(commit_sha, "evidence")
    if not evidence:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        evidence = intel_data["evidence"]
    
    start = (page - 1) * size
    end = start + size
    return {
        "total": len(evidence),
        "page": page,
        "size": size,
        "evidence": evidence[start:end]
    }


@app.get("/evaluations/{id}/recommendations")
async def get_evaluation_recommendations(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    commit_sha = evaluation.snapshot.commit_sha
    recommendations = RepositoryAnalysisCache.get_artifact(commit_sha, "recommendations")
    if not recommendations:
        from intelligence.intelligence_service import run_repository_intelligence
        intel_data = run_repository_intelligence(db, evaluation, evaluation.snapshot.snapshot_id)
        recommendations = intel_data["recommendations"]
    return recommendations


@app.get("/evaluations/{id}/timeline")
async def get_evaluation_timeline(id: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    
    timeline = []
    curr = evaluation.snapshot
    while curr:
        linked_eval = db.query(Evaluation).filter(Evaluation.repository_snapshot_id == curr.snapshot_id).first()
        timeline.insert(0, {
            "snapshot_id": curr.snapshot_id,
            "commit_sha": curr.commit_sha,
            "timestamp": curr.snapshot_timestamp.isoformat(),
            "evaluation_id": linked_eval.evaluation_id if linked_eval else None,
            "score": linked_eval.overall_score if linked_eval else None,
            "verdict": linked_eval.verdict if linked_eval else None
        })
        if curr.previous_snapshot_id:
            curr = db.query(RepositorySnapshot).filter(RepositorySnapshot.snapshot_id == curr.previous_snapshot_id).first()
        else:
            curr = None
    return timeline


@app.get("/evaluations/{id}/file/{path:path}")
async def get_evaluation_file_content(id: str, path: str, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(Evaluation.evaluation_id == id).first()
    if not evaluation or not evaluation.snapshot:
        raise HTTPException(status_code=404, detail="Evaluation or snapshot not found")
    
    commit_sha = evaluation.snapshot.commit_sha
    
    from intelligence.intelligence_service import _load_source_contents_from_github_cache
    contents = _load_source_contents_from_github_cache(evaluation.snapshot.repository.github_url)
    
    file_content = contents.get(path)
    if file_content is None:
        file_content = "// Content not cached in sample budget"
        
    metrics = RepositoryAnalysisCache.get_artifact(commit_sha, "metrics") or {}
    evidence = RepositoryAnalysisCache.get_artifact(commit_sha, "evidence") or []
    
    file_metrics = metrics.get(path, {})
    file_evidence = [ev for ev in evidence if ev["file_path"] == path]
    
    return {
        "path": path,
        "content": file_content,
        "metrics": file_metrics,
        "evidence": file_evidence
    }


# ── Webhook APIs ──────────────────────────────────────────────────────────────

@app.post("/webhooks/github", summary="GitHub repository commit webhook endpoint")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    headers = dict(request.headers)
    
    from utils.git_provider import GitHubProvider
    provider = GitHubProvider()
    event = provider.parse_webhook(payload, headers)
    
    if not event:
        return {"status": "ignored"}
        
    if event.get("type") == "ping":
        return {"status": "pong"}
        
    github_url = event.get("github_url")
    commit_sha = event.get("commit_sha")
    
    if not github_url:
        return {"status": "missing repository url"}
        
    normalized_url = validate_github_url(github_url)
    project = db.query(Project).filter(Project.github_url == normalized_url).first()
    if not project:
        return {"status": "no matching project found"}
        
    existing_snapshot = db.query(RepositorySnapshot).filter(
        RepositorySnapshot.commit_sha == commit_sha,
        RepositorySnapshot.repository.has(project_id=project.id)
    ).first()
    
    if existing_snapshot:
        return {"status": "commit already evaluated", "snapshot_id": existing_snapshot.snapshot_id}
        
    project.status = "pending"
    db.commit()
    background_tasks.add_task(_run_evaluation_background, project.id)
    return {"status": "triggered evaluation", "project_id": project.id, "commit_sha": commit_sha}


@app.post("/webhooks/gitlab", summary="GitLab repository commit webhook endpoint")
async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    repo_data = payload.get("project", {})
    gitlab_url = repo_data.get("http_url")
    commit_sha = payload.get("checkout_sha")
    
    if not gitlab_url or not commit_sha:
        return {"status": "ignored"}
        
    project = db.query(Project).filter(Project.github_url == gitlab_url).first()
    if not project:
        return {"status": "no matching project found"}
        
    project.status = "pending"
    db.commit()
    background_tasks.add_task(_run_evaluation_background, project.id)
    return {"status": "triggered gitlab evaluation", "project_id": project.id}


@app.post("/webhooks/bitbucket", summary="Bitbucket repository commit webhook endpoint")
async def bitbucket_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    repo_data = payload.get("repository", {})
    links = repo_data.get("links", {})
    html_link = links.get("html", {})
    bitbucket_url = html_link.get("href")
    
    push = payload.get("push", {})
    changes = push.get("changes", [])
    commit_sha = None
    if changes:
        new_change = changes[0].get("new", {})
        target = new_change.get("target", {})
        commit_sha = target.get("hash")
        
    if not bitbucket_url or not commit_sha:
        return {"status": "ignored"}
        
    project = db.query(Project).filter(Project.github_url == bitbucket_url).first()
    if not project:
        return {"status": "no matching project found"}
        
    project.status = "pending"
    db.commit()
    background_tasks.add_task(_run_evaluation_background, project.id)
    return {"status": "triggered bitbucket evaluation", "project_id": project.id}
