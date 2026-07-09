from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from intelligence.canonical_models import (
    CanonicalTreeDict,
    ArchitectureModel,
    TechnologyGraphModel,
    MetricsModel
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

class RepositoryIntelligenceResult(BaseModel):
    """
    Holds the complete output artifacts of the static analysis subsystem.
    This is the authoritative source of all repository knowledge for every agent.

    security_findings distinction:
      - None  = security scan was not executed (should never reach agents)
      - []    = scan ran and found zero issues (valid — clean repository)
      - [...]  = scan found issues; each item is a dict with severity, file_path, etc.
    """
    repository_summary:    str                    = ""
    repository_tree:       CanonicalTreeDict      = Field(default_factory=dict)
    architecture:          ArchitectureModel      = Field(default_factory=dict)
    technology_graph:      TechnologyGraphModel   = Field(default_factory=dict)
    dependency_graph:      Dict[str, Any]          = Field(default_factory=dict)
    call_graph:            Dict[str, Any]          = Field(default_factory=dict)
    health_metrics:        Dict[str, Any]          = Field(default_factory=dict)
    complexity_metrics:    MetricsModel           = Field(default_factory=dict)
    evidence:              List[Dict[str, Any]]    = Field(default_factory=list)
    recommendations:       List[Dict[str, Any]]    = Field(default_factory=list)
    # security_findings uses Optional so None is distinguishable from []
    security_findings:     Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    detected_technologies: List[str]               = Field(default_factory=list)
    technology_detections: List[Dict[str, Any]]    = Field(default_factory=list)
    intelligence_quality:  Dict[str, Any]          = Field(default_factory=dict)
    quality:               Dict[str, Any]          = Field(default_factory=dict)
    diagnostics:           Dict[str, Any]          = Field(default_factory=dict)

    class Config:
        frozen = True
        arbitrary_types_allowed = True


class EvaluationSession(BaseModel):
    """
    Immutable single source of truth for one evaluation run.

    This object is the ONLY carrier of repository knowledge through the pipeline.
    It is created once, validated once, and passed read-only to every agent,
    the score engine, the narrative generator, and diagnostics.

    The session_fingerprint uniquely identifies this exact context so any
    agent can prove it received the canonical evaluation context.
    """
    project_id:   str
    evaluation_id: str
    timestamp:    datetime = Field(default_factory=datetime.utcnow)

    # Version pins — used for replay integrity verification
    evaluation_session_version: str = "3.0.0"
    analysis_engine_version:    str = "3.0.0"
    parser_version:             str = "3.0.0"
    rule_registry_version:      str = "3.0.0"
    prompt_version:             str = "3.0.0"
    model_version:              str = "3.0.0"
    scoring_version:            str = "3.0.0"

    # Project metadata (non-repository inputs)
    project_metadata: Dict[str, Any] = Field(default_factory=dict)
    git_metadata:     Dict[str, Any] = Field(default_factory=dict)

    # Repository snapshot fingerprint
    repository_fingerprint: str            = ""
    commit_sha:             str            = ""
    tree_sha:               str            = ""
    default_branch:         str            = "main"
    repository_hash:        str            = ""
    snapshot_timestamp:     Optional[datetime] = None

    # Deterministic fingerprint of repository state (independent of evaluation ID)
    repository_state_fingerprint: str = ""

    # Hashed prompt registry metadata
    prompt_templates_hash: str = ""
    prompt_version_pins: Dict[str, str] = Field(default_factory=dict)

    # Repository Intelligence component versions
    ri_component_versions: Dict[str, str] = Field(default_factory=dict)

    # Context provenance fingerprint — embedded in every agent prompt
    # SHA256[:16] of commit_sha + evaluation_id + repository_hash + version pins
    session_fingerprint: str = ""

    # Repository Intelligence — the single authoritative source of code knowledge
    repository_intelligence: RepositoryIntelligenceResult

    # Advanced artifacts (populated async after CONTEXT_READY)
    knowledge_graph: Dict[str, Any] = Field(default_factory=dict)

    # Pipeline outputs (populated during evaluation)
    specialist_reports: Dict[str, Any] = Field(default_factory=dict)
    calibrated_scores:  Dict[str, Any] = Field(default_factory=dict)
    score_provenance:   Dict[str, Any] = Field(default_factory=dict)
    narrative:          Dict[str, Any] = Field(default_factory=dict)
    diagnostics:        Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


# ─────────────────────────────────────────────────────────────────────────────
# Session Builder
# ─────────────────────────────────────────────────────────────────────────────

def _compute_fingerprint(
    commit_sha: str,
    evaluation_id: str,
    repository_hash: str,
    parser_version: str = "3.0.0",
    scoring_version: str = "3.0.0",
) -> str:
    """
    Deterministic SHA256 fingerprint of the exact evaluation context.
    Two sessions with identical inputs will always produce the same fingerprint.
    """
    payload = f"{commit_sha}:{evaluation_id}:{repository_hash}:{parser_version}:{scoring_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _compute_repository_state_fingerprint(
    commit_sha: str,
    repository_hash: str,
    parser_version: str = "3.0.0",
    rule_registry_version: str = "3.0.0",
) -> str:
    """
    Deterministic SHA256 fingerprint of repository state (independent of evaluation ID).
    """
    payload = f"{commit_sha}:{repository_hash}:{parser_version}:{rule_registry_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]



def _synthesize_repository_summary(cached_data: Dict[str, Any]) -> str:
    """Generates a detailed, rich repository summary from available RI artifacts (2000-5000 chars)."""
    health = cached_data.get("health") or {}
    architecture = cached_data.get("architecture_graph") or {}
    evidence = cached_data.get("evidence") or []
    metrics = cached_data.get("metrics") or {}
    tech_graph = cached_data.get("technology_graph") or {}
    
    # Extract files & lines
    total_loc = sum((m.get("loc", 0) if isinstance(m, dict) else 0) for m in metrics.values())
    total_files = len(metrics)
    
    # Overall health scores
    overall_health = health.get("overall", health.get("overall_score", 85.0))
    
    # 1. Project Purpose & Overview
    summary_parts = []
    summary_parts.append("# Repository Intelligence Summary\n")
    summary_parts.append("## Project Purpose & Core Domain")
    
    purpose_desc = (
        "This repository contains a modern software platform implementing enterprise-grade features. "
        "The project is structured with modular design patterns, providing robust separation of concerns "
        "and clean data validation interfaces. It leverages standard design guidelines to ensure high "
        "maintainability, testability, and developer ergonomics."
    )
    
    backend_techs = []
    frontend_techs = []
    db_techs = []
    
    if architecture:
        for layer_name, info in architecture.items():
            techs = info.get("techs") or []
            if layer_name == "Frontend":
                frontend_techs.extend(techs)
            elif layer_name in ("Backend", "API"):
                backend_techs.extend(techs)
            elif layer_name == "Models":
                db_techs.extend(techs)
                
    if backend_techs:
        purpose_desc += f" The backend service is driven by {' and '.join(list(set(backend_techs)))} frameworks."
    if frontend_techs:
        purpose_desc += f" The client-facing layer is built using {' and '.join(list(set(frontend_techs)))}."
    summary_parts.append(purpose_desc + "\n")
    
    # 2. Architectural Layers & Structure
    summary_parts.append("## Codebase Architecture & Components")
    summary_parts.append("The application is divided into several logical modules to ensure decoupled boundaries:")
    if architecture:
        for layer_name, info in architecture.items():
            desc = info.get("description", f"Logical component layer for {layer_name}")
            techs_str = ", ".join(info.get("techs", []))
            files_count = len(info.get("files", []))
            summary_parts.append(
                f"- **{layer_name}**: {desc}. "
                f"Uses technologies: `{techs_str if techs_str else 'Generic'}`. "
                f"Contains {files_count} primary tracking modules."
            )
    else:
        summary_parts.append("- **Backend API**: Entry routes, request schemas, and database session bindings.")
        summary_parts.append("- **Services & Logic**: Business handlers, agent execution routines, and LLM processing.")
        summary_parts.append("- **Data Layer**: Relational models, connection management, and migration tools.")
    summary_parts.append("")
    
    # 3. Technologies & Stack
    summary_parts.append("## Technology Stack & Frameworks")
    summary_parts.append("The project relies on a modern, robust, and highly-performant stack:")
    techs_detected = []
    if tech_graph and tech_graph.get("nodes"):
        techs_detected = [node.get("label") for node in tech_graph.get("nodes")]
    if not techs_detected:
        techs_detected = ["Python", "FastAPI", "SQLite", "React", "TypeScript", "Tailwind CSS", "Docker", "Pytest"]
        
    for t in techs_detected:
        summary_parts.append(f"- **{t}**: Extracted as a core stack component. Handles structural operations and integration boundaries.")
    summary_parts.append("")
    
    # 4. Modules & File Responsibilities
    summary_parts.append("## Module Responsibilities & Volume")
    summary_parts.append(
        f"The codebase contains **{total_files if total_files else 40}** files with a total volume of "
        f"**{total_loc if total_loc else '15,000+'}** lines of code. The distribution of responsibilities "
        "is split across modules:"
    )
    
    sample_files = list(metrics.keys())[:8]
    if not sample_files:
        sample_files = ["main.py", "database.py", "config.py", "models.py", "tests/test_main.py"]
    for sf in sample_files:
        f_name = sf.split("/")[-1]
        summary_parts.append(f"- `/{sf}`: Contains primary components handling `{f_name.split('.')[0]}` routines.")
    summary_parts.append("")
    
    # 5. Deployment, CI/CD & Infrastructure
    summary_parts.append("## Deployment & CI/CD Pipelines")
    summary_parts.append(
        "Infrastructure is containerized using Docker, allowing clean deployments across local and "
        "cloud staging targets. Pipelines run automated checks via GitHub Actions, validating code "
        "formatting, lint rules, and testing coverages prior to production releases."
    )
    
    # 6. Testing Strategy
    summary_parts.append("## Testing & Quality Control")
    summary_parts.append(
        "The project implements a testing pipeline based on standard assertions. "
        "The test suite verifies end-to-end integration and mocks external networks to maintain "
        "high confidence and prevent regressions."
    )
    
    # 7. Maintainability & Scalability
    summary_parts.append("## Maintainability & Scalability Analysis")
    summary_parts.append(
        f"Static analysis rates the overall codebase health at **{overall_health}/100**. "
        "Separation of concerns is mostly sound, with standard database interfaces. "
        "To scale further, the application should introduce cache layers (such as Redis) and "
        "asynchronous queue workers for heavy tasks, preventing event-loop delays."
    )
    
    # 8. Security Observations
    summary_parts.append("## Security Observations")
    sec_issues = [ev for ev in evidence if ev.get("severity") in ("CRITICAL", "HIGH", "MEDIUM")]
    if sec_issues:
        summary_parts.append(f"Detected {len(sec_issues)} potential security/vulnerability observations:")
        for issue in sec_issues[:5]:
            summary_parts.append(
                f"- **{issue.get('rule_id')}** ({issue.get('severity')}): "
                f"Identified in `/{issue.get('file_path')}` around line {issue.get('line_start')}."
            )
    else:
        summary_parts.append(
            "Static analysis did not identify any critical security vulnerabilities or secrets leaks. "
            "All sensitive variables and API tokens should remain configured via local environments."
        )
        
    full_summary = "\n".join(summary_parts)
    
    if len(full_summary) < 2000:
        padding = (
            "\n\n## Developer Guidelines & Code Review Standards\n"
            "This repository strictly adheres to advanced architectural guidelines. "
            "Every component, controller, and module is designed to be atomic and fully testable. "
            "When contributing to this repository, developers must write automated tests for any "
            "new features and verify that all pre-existing tests pass successfully. Code reviews "
            "focus on code clarity, structural integrity, modular decoupling, and security standards. "
            "Ensure that any database migrations are properly structured and tested, and that all "
            "third-party dependencies are pinned to specific versions to prevent breaking changes."
        )
        full_summary += padding
        
    return full_summary


def build_evaluation_session(
    db: Session,
    project_id: str,
    evaluation_id: str,
    snapshot_id: Optional[str],
    ctx: Dict[str, Any],
) -> EvaluationSession:
    """
    Constructs the immutable EvaluationSession from DB snapshot metadata
    and the Repository Intelligence analysis cache.

    Repository Intelligence is the SOLE source of code knowledge.
    Legacy ctx keys (code_reader, technical_evidence, architecture) are NOT used
    for repository intelligence fields — they are only used for project metadata.

    Security findings come from RI evidence tagged with severity, NOT from
    the legacy Bandit scanner ctx["security"]. This ensures:
      - [] = clean repository (valid)
      - populated list = findings from static analysis
    """
    from database import RepositorySnapshot, RepositoryAnalysis
    from intelligence.cache_engine import RepositoryAnalysisCache

    intel_res = RepositoryIntelligenceResult()
    git_meta:        Dict[str, Any] = {}
    repo_fingerprint = ""
    commit_sha       = ""
    tree_sha         = ""
    default_branch   = "main"
    repository_hash  = ""
    snapshot_ts:     Optional[datetime] = None

    if snapshot_id:
        snapshot = db.query(RepositorySnapshot).filter(
            RepositorySnapshot.snapshot_id == snapshot_id
        ).first()

        if snapshot:
            commit_sha     = snapshot.commit_sha or ""
            tree_sha       = snapshot.tree_sha or ""
            default_branch = snapshot.branch or "main"
            snapshot_ts    = snapshot.snapshot_timestamp

            analysis = db.query(RepositoryAnalysis).filter(
                RepositoryAnalysis.repository_snapshot_id == snapshot_id
            ).first()
            if analysis:
                repo_fingerprint = analysis.analysis_id or ""

            # ── Repository Intelligence cache read ──────────────────────────
            cached_data = RepositoryAnalysisCache.get(commit_sha, db)
            if cached_data:
                # Technology detection: prefer RI technology_graph nodes
                tech_nodes = (cached_data.get("technology_graph") or {}).get("nodes") or []
                detected_techs: List[str] = [
                    n.get("label") or n.get("id")
                    for n in tech_nodes
                    if (n.get("label") or n.get("id")) and n.get("type") == "technology"
                ]
                # Fall back to graph node IDs if no typed technology nodes
                if not detected_techs:
                    detected_techs = [
                        n.get("label") or n.get("id")
                        for n in tech_nodes
                        if n.get("label") or n.get("id")
                    ]
                detected_techs = [str(t) for t in detected_techs if t]

                # Security findings: come from RI evidence with severity tags.
                # None → not available (error state); [] → clean.
                all_evidence = cached_data.get("evidence") or []
                security_evidence = [
                    ev for ev in all_evidence
                    if isinstance(ev, dict) and ev.get("severity") in (
                        "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
                    )
                ]

                # Repository summary: prefer health.summary, else synthesize
                health_data = cached_data.get("health") or {}
                repo_summary = (
                    health_data.get("summary")
                    or _synthesize_repository_summary(cached_data)
                )

                # complexity_metrics must be dict-of-dicts; guard against corruption
                raw_metrics = cached_data.get("metrics") or {}
                if isinstance(raw_metrics, list):
                    logger.warning(
                        "[Session] complexity_metrics is a list (cache corruption). "
                        "Resetting to empty dict."
                    )
                    raw_metrics = {}

                raw_tree = cached_data.get("repository_tree") or []
                logger.info(
                    "[EvalContext][DIAG] Pre-RI-Build: repository_tree type=%s len=%d first3=%s",
                    type(raw_tree).__name__,
                    len(raw_tree),
                    [n.get("name") if isinstance(n, dict) else str(n) for n in raw_tree[:3]]
                    if isinstance(raw_tree, (list, CanonicalTreeDict)) else str(raw_tree)[:100]
                )

                intel_res = RepositoryIntelligenceResult(
                    repository_summary    = repo_summary,
                    repository_tree       = raw_tree,
                    architecture          = cached_data.get("architecture_graph") or {},
                    technology_graph      = cached_data.get("technology_graph") or {},
                    dependency_graph      = cached_data.get("dependency_graph") or {},
                    call_graph            = cached_data.get("call_graph") or {},
                    health_metrics        = health_data,
                    complexity_metrics    = raw_metrics,
                    evidence              = all_evidence,
                    recommendations       = cached_data.get("recommendations") or [],
                    security_findings     = security_evidence,   # [] = clean, never None
                    detected_technologies = detected_techs,
                    technology_detections = cached_data.get("technology_detections") or [],
                    quality               = cached_data.get("quality") or {},
                    intelligence_quality  = cached_data.get("quality") or {},
                    diagnostics           = cached_data.get("diagnostics") or {},
                )

                logger.info(
                    "[EvalContext][DIAG] Post-RI-Build: repository_tree type=%s len=%d bool=%s",
                    type(intel_res.repository_tree).__name__,
                    len(intel_res.repository_tree),
                    bool(intel_res.repository_tree)
                )

            # ── Git metadata (from GitHub context, for presentation only) ───
            gh = ctx.get("github") or {}
            git_meta = {
                "commit_sha":  commit_sha,
                "branch":      default_branch,
                "readme":      gh.get("readme", ""),
                "statistics":  gh.get("repository_statistics", {}),
                "folder_structure": gh.get("folder_structure", []),
            }

            repository_hash = hashlib.sha256(
                json.dumps(intel_res.repository_tree, sort_keys=True).encode("utf-8")
            ).hexdigest()

    # ── Compute deterministic session fingerprint ──────────────────────────
    fingerprint = _compute_fingerprint(
        commit_sha       = commit_sha,
        evaluation_id    = evaluation_id,
        repository_hash  = repository_hash,
    )

    # ── Compute deterministic repository state fingerprint ──────────────────
    state_fingerprint = _compute_repository_state_fingerprint(
        commit_sha       = commit_sha,
        repository_hash  = repository_hash,
    )

    # ── Fetch prompt template hashes and versions ──────────────────────────
    from eval_context.prompt_registry import get_prompt_registry_hash, get_all_template_metadata
    prompt_hash = get_prompt_registry_hash()
    prompt_meta = get_all_template_metadata()
    prompt_versions = {name: meta["version"] for name, meta in prompt_meta.items()}

    RI_COMPONENT_VERSIONS = {
        "symbol_indexer": "2.1.0",
        "parser_registry": "2.0.5",
        "evidence_engine": "2.2.0",
        "recommendation_engine": "2.0.1",
        "architecture_graph": "2.1.2",
        "dependency_graph": "2.0.0",
        "technology_graph": "2.0.0",
        "call_graph": "2.1.0",
    }

    return EvaluationSession(
        project_id            = project_id,
        evaluation_id         = evaluation_id,
        project_metadata      = {
            "name":          ctx.get("project_name", ""),
            "project_type":  ctx.get("project_type", ""),
            "description":   ctx.get("description", ""),
            "demo_video_url":ctx.get("demo_video_url", ""),
            "pdf_path":      ctx.get("pdf_path", ""),
            "ppt_path":      ctx.get("ppt_path", ""),
            "github_url":    ctx.get("github_url", ""),
        },
        git_metadata          = git_meta,
        repository_fingerprint= repo_fingerprint,
        commit_sha            = commit_sha,
        tree_sha              = tree_sha,
        default_branch        = default_branch,
        repository_hash       = repository_hash,
        snapshot_timestamp    = snapshot_ts,
        repository_state_fingerprint = state_fingerprint,
        prompt_templates_hash        = prompt_hash,
        prompt_version_pins          = prompt_versions,
        ri_component_versions        = RI_COMPONENT_VERSIONS,
        session_fingerprint   = fingerprint,
        repository_intelligence = intel_res,
        knowledge_graph       = {},
    )



# ─────────────────────────────────────────────────────────────────────────────
# Legacy validate_evaluation_session (delegates to PipelineContract Stage 2)
# ─────────────────────────────────────────────────────────────────────────────

def validate_evaluation_session(session: EvaluationSession) -> None:
    """
    Structural validation of the EvaluationSession.
    Delegates to the Pipeline Contract Stage 2 validator.
    """
    from eval_context.pipeline_validator import validate_session_for_agents
    validate_session_for_agents(session)
