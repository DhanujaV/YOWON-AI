"""
pipeline_validator.py — Pipeline Contract for YOWON AI.

Every evaluation stage must pass through a validation gate before proceeding.
Raises EvaluationIncompleteException with structured diagnostics on any failure.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from validation.schemas import EvaluationIncompleteException

logger = logging.getLogger(__name__)

from intelligence.canonical_models import (
    CanonicalTreeDict,
    ArchitectureModel,
    TechnologyGraphModel,
    MetricsModel
)

# (key, expected_type, min_length, required)
# min_length = 0 → non-empty not required (may be genuinely empty)
# required   = True → key must exist and not be None
_ARTIFACT_CONTRACT: List[tuple] = [
    ("repository_tree",   CanonicalTreeDict, 1,  True),   # must have at least 1 node
    ("health",            dict, 1,  True),   # must have at least 1 key
    ("evidence",          list, 0,  True),   # may be empty (clean repo)
    ("metrics",           MetricsModel, 0,  True),   # may be empty (no source files)
    ("architecture_graph",ArchitectureModel, 0,  True),   # may be empty (no patterns detected)
    ("dependency_graph",  dict, 0,  True),   # may be empty
    ("technology_graph",  TechnologyGraphModel, 0,  True),   # may be empty
    ("recommendations",   list, 0,  True),   # may be empty
]


def validate_intelligence_artifacts(data: Dict[str, Any]) -> None:
    """
    Pipeline Contract — Stage 1: Repository Intelligence → EvaluationSession.

    Validates that every required Repository Intelligence artifact exists,
    has the correct type, and meets minimum completeness thresholds.

    Security findings are NOT validated here because:
      - None  = scanning was not run (should not happen, but handled downstream)
      - []    = scanning found no issues (valid — clean repository)

    Raises EvaluationIncompleteException with structured diagnostics.
    """
    # ── DIAGNOSTIC: log what the validator receives ───────────────────────
    tree = data.get("repository_tree")
    logger.info(
        "[Validator][DIAG] Stage 1 received: repository_tree type=%s len=%d",
        type(tree).__name__ if tree is not None else "NoneType",
        len(tree) if tree is not None else 0
    )

    failures: List[str] = []

    for key, expected_type, min_len, required in _ARTIFACT_CONTRACT:
        val = data.get(key)

        if required and val is None:
            failures.append(f"artifact '{key}' is missing (None)")
            continue

        if val is None:
            continue  # optional, skip

        # Special case: repository_tree can be plain list OR CanonicalTreeDict
        if key == "repository_tree":
            if not isinstance(val, (list, CanonicalTreeDict)):
                failures.append(
                    f"artifact '{key}' has wrong type: "
                    f"expected list or CanonicalTreeDict, got {type(val).__name__}"
                )
                continue
            if min_len > 0 and len(val) < min_len:
                failures.append(
                    f"artifact '{key}' is empty — minimum {min_len} item(s) required"
                )
            continue

        if not isinstance(val, expected_type):
            failures.append(
                f"artifact '{key}' has wrong type: "
                f"expected {expected_type.__name__}, got {type(val).__name__}"
            )
            continue

        if min_len > 0 and len(val) < min_len:
            failures.append(
                f"artifact '{key}' is empty — minimum {min_len} item(s) required"
            )

    if failures:
        diagnostic = "; ".join(failures)
        logger.error("[PipelineContract] Intelligence artifact validation failed: %s", diagnostic)
        raise EvaluationIncompleteException(
            f"Repository Intelligence produced incomplete artifacts: {diagnostic}",
            details={"stage": "intelligence_to_session", "failures": failures},
        )

    # Additional semantic check: metrics must be a dict-of-dicts (file_path → metrics),
    # not a list or primitive. Corrupted cache sometimes returns a list.
    metrics = data.get("metrics")
    if metrics and isinstance(metrics, dict):
        sample = next(iter(metrics.values()), None)
        if sample is not None and not isinstance(sample, dict):
            raise EvaluationIncompleteException(
                "Repository Intelligence 'metrics' artifact is corrupt — "
                f"expected dict-of-dicts, values are {type(sample).__name__}",
                details={"stage": "intelligence_to_session", "failures": ["metrics_corrupt"]},
            )

    logger.info(
        "[PipelineContract] Stage 1 PASSED — tree=%d nodes, evidence=%d records, health_keys=%d",
        len(data.get("repository_tree") or []),
        len(data.get("evidence") or []),
        len(data.get("health") or {}),
    )


def validate_session_for_agents(session: Any) -> None:
    """
    Pipeline Contract — Stage 2: EvaluationSession → Specialist Agents.

    Validates that the immutable EvaluationSession contains all fields
    required for agents to evaluate without reconstructing repository knowledge.

    Parameters
    ----------
    session : EvaluationSession
        The immutable session object.
    """
    failures: List[str] = []
    intel = session.repository_intelligence

    is_repo_eval = bool(
        session.project_metadata.get("github_url") or session.commit_sha
    )

    if is_repo_eval:
        if not intel.repository_summary:
            failures.append("repository_summary is empty")
        if not intel.repository_tree:
            failures.append("repository_tree is empty")
        if not intel.health_metrics:
            failures.append("health_metrics is empty")
        # security_findings: None → treat as [] (no scan ran / clean repo)
        if intel.security_findings is None:
            logger.warning(
                "[PipelineContract] Stage 2: security_findings is None — "
                "treating as empty (no security scan data). Evaluation proceeds."
            )
        # evidence: required to be non-None but may be legitimately empty
        if intel.evidence is None:
            failures.append("evidence is None")
        if not intel.detected_technologies:
            failures.append("detected_technologies is empty")
        # dependency_graph and complexity_metrics are optional — warn only
        if not intel.dependency_graph:
            logger.warning(
                "[PipelineContract] Stage 2: dependency_graph is empty — "
                "repo may have no parseable manifest files. Proceeding."
            )
        if not intel.complexity_metrics:
            logger.warning(
                "[PipelineContract] Stage 2: complexity_metrics is empty — "
                "repo may have no analyzable source files. Proceeding."
            )
        # recommendations may be empty for clean/minimal repos — warn only
        if not intel.recommendations:
            logger.warning(
                "[PipelineContract] Stage 2: recommendations is empty — "
                "repo may have no actionable recommendations. Proceeding."
            )

    if not session.session_fingerprint:
        failures.append("session_fingerprint is missing — context provenance broken")

    if failures:
        diagnostic = "; ".join(failures)
        logger.error("[PipelineContract] EvaluationSession validation failed: %s", diagnostic)
        raise EvaluationIncompleteException(
            f"EvaluationSession is incomplete — agents cannot evaluate: {diagnostic}",
            details={"stage": "session_to_agents", "failures": failures},
        )

    logger.info(
        "[PipelineContract] Stage 2 PASSED — fingerprint=%s evidence=%d techs=%d",
        session.session_fingerprint,
        len(intel.evidence or []),
        len(intel.detected_technologies or []),
    )


def validate_agent_output(name: str, report: Any, parse_source: str) -> None:
    """
    Pipeline Contract — Stage 3: Agent Output → Score Engine.

    Fails fast if an agent produced a fallback/degraded output.
    No fallback scores may reach the score engine.

    Parameters
    ----------
    name        : Agent name (technical, security, innovation, risk, presentation)
    report      : The parsed agent report (Pydantic model)
    parse_source: Source of the parse ('llm', 'merged', 'fallback')
    """
    if parse_source == "fallback":
        raise EvaluationIncompleteException(
            f"Agent '{name}' produced a fallback score — LLM output was unparseable. "
            f"Cannot use fabricated default scores. Evaluation aborted.",
            details={"stage": "agent_to_score_engine", "agent": name, "parse_source": parse_source},
        )

    if parse_source == "merged":
        # merged = JSON was partial but score field was salvaged — emit a warning but allow it
        logger.warning(
            "[PipelineContract] Agent '%s' produced a merged score (partial JSON). "
            "Proceeding with caution.",
            name,
        )

    # Type-specific score range check (belt-and-suspenders)
    score_field_map = {
        "technical":    "technical_score",
        "security":     "security_score",
        "innovation":   "innovation_score",
        "presentation": "presentation_score",
        "risk":         "impact_score",
    }
    score_field = score_field_map.get(name)
    if score_field:
        score = getattr(report, score_field, None)
        if score is None or not isinstance(score, (int, float)):
            raise EvaluationIncompleteException(
                f"Agent '{name}' score field '{score_field}' is missing or non-numeric: {score!r}",
                details={"stage": "agent_to_score_engine", "agent": name, "field": score_field},
            )
        if not (0 <= int(score) <= 100):
            raise EvaluationIncompleteException(
                f"Agent '{name}' score {score} is out of valid range [0, 100]",
                details={"stage": "agent_to_score_engine", "agent": name, "score": score},
            )

    logger.debug("[PipelineContract] Stage 3 agent='%s' source='%s' PASSED", name, parse_source)


def log_pipeline_banner(
    cached_data: Dict[str, Any],
    session: Optional[Any] = None,
    execution_time_seconds: float = 0.0,
) -> None:
    """Emits a structured production log banner after Repository Intelligence completes."""
    tree = cached_data.get("repository_tree") or []
    arch = cached_data.get("architecture_graph") or {}
    tech = cached_data.get("technology_graph") or {}
    dep = cached_data.get("dependency_graph") or {}
    evidence = cached_data.get("evidence") or []
    metrics = cached_data.get("metrics") or {}
    health = cached_data.get("health") or {}
    recs = cached_data.get("recommendations") or []

    def _check(val, threshold: int = 1) -> str:
        return "✓" if (val and len(val) >= threshold) else "✗"

    lines = [
        "=" * 52,
        "REPOSITORY INTELLIGENCE",
        "=" * 52,
        f"  Repository Tree      {_check(tree)} ({len(tree)} nodes)",
        f"  Architecture         {_check(arch)} ({len(arch)} layers)",
        f"  Technology Graph     {_check(tech.get('nodes', []))} ({len(tech.get('nodes', []))} nodes)",
        f"  Dependency Graph     {_check(dep)}",
        f"  Evidence             {_check(evidence, 0)} ({len(evidence)} records)",
        f"  Metrics              {_check(metrics, 0)} ({len(metrics)} files)",
        f"  Health Metrics       {_check(health)}",
        f"  Recommendations      {_check(recs, 0)} ({len(recs)} items)",
        f"  Execution Time       {execution_time_seconds:.2f}s",
        "=" * 52,
    ]

    if session:
        intel = session.repository_intelligence
        lines += [
            "EVALUATION SESSION",
            "=" * 52,
            f"  Session Fingerprint  {session.session_fingerprint}",
            f"  Repository Summary   {len(intel.repository_summary)} chars",
            f"  Tree Nodes           {len(intel.repository_tree)}",
            f"  Architecture         {len(intel.architecture)} layers",
            f"  Dependencies         {len(intel.dependency_graph)} keys",
            f"  Evidence             {len(intel.evidence)} records",
            f"  Security Findings    {len(intel.security_findings)} findings",
            f"  Technologies         {len(intel.detected_technologies)} detected",
            f"  Health Metrics       {len(intel.health_metrics)} keys",
            f"  Recommendations      {len(intel.recommendations)} items",
            "=" * 52,
        ]

    for line in lines:
        logger.info("[Intel] %s", line)


def validate_repository_intelligence_completeness(session: Any) -> None:
    """
    Pipeline Contract — Stage 4: Repository Intelligence Completeness Gate.

    Rejects the evaluation if critical RI artifacts (Architecture, Technology,
    Evidence, Knowledge, Dependency graphs) are empty or fail quality thresholds,
    unless the repository contains no source code files.
    """
    failures: List[str] = []
    warnings: List[str] = []
    intel = session.repository_intelligence

    # ── DIAGNOSTIC: Log Stage 4 inputs ───────────────────────────────────
    logger.info(
        "[Validator][DIAG] Stage 4 received: repository_tree type=%s len=%d bool=%s",
        type(intel.repository_tree).__name__,
        len(intel.repository_tree),
        bool(intel.repository_tree)
    )
    if intel.repository_tree:
        first_nodes = list(intel.repository_tree)[:3]
        for n in first_nodes:
            if isinstance(n, dict):
                logger.info("[Validator][DIAG] Stage 4 tree node: name=%s type=%s", n.get("name"), n.get("type"))

    # Check if this repository actually has analyzable code
    # Uses recursive scan because tree is hierarchical (files are inside directories)
    CODE_EXTENSIONS = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cs")

    def _has_code_recursive(nodes) -> bool:
        """Recursively scan nested tree nodes to find any code files."""
        if not nodes:
            return False
        for node in nodes:
            if not isinstance(node, dict):
                continue
            ntype = node.get("type", "")
            npath = node.get("path", "")
            if ntype == "file" and any(npath.endswith(ext) for ext in CODE_EXTENSIONS):
                return True
            # Recurse into directory children
            children = node.get("children", [])
            if children and _has_code_recursive(children):
                return True
        return False

    has_code = _has_code_recursive(list(intel.repository_tree))
    logger.info("[Validator][DIAG] Stage 4 has_code=%s", has_code)

    if not has_code:
        logger.warning("[PipelineContract] Stage 4 SKIPPED — repository lacks analyzable code files")
        return


    # 1. Architecture Graph validation
    arch = intel.architecture
    arch_nodes = []
    if isinstance(arch, dict):
        arch_nodes = arch.get("nodes") or []
    elif hasattr(arch, "get"):
        arch_nodes = arch.get("nodes") or []

    if len(arch_nodes) == 0:
        failures.append("Architecture Graph is empty — no architecture layers detected")

    # 2. Technology Graph validation
    tech = intel.technology_graph
    tech_nodes = []
    if isinstance(tech, dict):
        tech_nodes = tech.get("nodes") or []
    elif hasattr(tech, "get"):
        tech_nodes = tech.get("nodes") or []

    if len(tech_nodes) == 0:
        warnings.append("Technology Graph has no nodes")

    # 3. Evidence count validation — empty evidence is valid (clean or doc-only repo)
    evidence_count = len(intel.evidence or [])
    if evidence_count == 0:
        logger.warning(
            "[PipelineContract] Stage 4: Evidence count is 0 — "
            "repository may be clean or documentation-only. Proceeding."
        )
    elif evidence_count < 3:
        logger.warning(
            "[PipelineContract] Stage 4: Evidence count (%d) is low. "
            "Repository may be minimal. Proceeding.", evidence_count
        )

    # 4. Dependency Graph validation
    dep = intel.dependency_graph
    dep_nodes = []
    if isinstance(dep, dict):
        dep_nodes = dep.get("nodes") or []
    elif hasattr(dep, "get"):
        dep_nodes = dep.get("nodes") or []

    if len(dep_nodes) == 0:
        warnings.append("Dependency Graph has no nodes")

    # 5. Quality Score threshold validation
    quality_overall = 0.0
    is_sufficient = True
    if hasattr(intel, "intelligence_quality") and intel.intelligence_quality:
        quality_overall = intel.intelligence_quality.get("overall_score") or 0.0
        is_sufficient = intel.intelligence_quality.get("is_sufficient", True)
    elif isinstance(getattr(intel, "quality", None), dict):
        quality_overall = intel.quality.get("overall_score") or 0.0
        is_sufficient = intel.quality.get("is_sufficient", True)
    elif hasattr(getattr(intel, "quality", None), "overall_score"):
        quality_overall = intel.quality.overall_score
        is_sufficient = intel.quality.is_sufficient

    if quality_overall > 0.0 and not is_sufficient:
        failures.append(f"Repository Intelligence Quality score ({quality_overall:.1f}%) is below sufficiency threshold")

    # Raise exception if any critical failures exist
    if failures:
        diagnostic = "; ".join(failures)
        logger.error("[PipelineContract] Stage 4 Repository Intelligence completeness check FAILED: %s", diagnostic)
        raise EvaluationIncompleteException(
            f"Repository Intelligence Completeness Gate validation failed: {diagnostic}",
            details={"stage": "ri_completeness_gate", "failures": failures, "warnings": warnings},
        )

    # Log warnings
    for warn in warnings:
        logger.warning("[PipelineContract] Stage 4 Warning: %s", warn)

    logger.info(
        "[PipelineContract] Stage 4 PASSED — quality=%.1f%% arch_nodes=%d tech_nodes=%d evidence=%d",
        quality_overall, len(arch_nodes), len(tech_nodes), evidence_count
    )

