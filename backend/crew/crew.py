"""
crew.py — Parallel evaluation pipeline with direct Ollama + CrewAI fallback.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from crewai import Agent, Crew, Process, Task

from agents.chief_evaluation_agent import create_chief_evaluation_agent
from agents.narrative_agent import create_narrative_agent
from agents.specialist_agents import (
    create_innovation_agent,
    create_presentation_agent,
    create_risk_agent,
    create_security_agent,
    create_technical_agent,
)
from config import (
    AGENT_MODEL_PROFILES,
    AGENT_TIMEOUT_SEC,
    EVALUATION_TIMEOUT_SEC,
    FAILED_AGENT_SCORE,
    OLLAMA_PARALLEL,
    USE_DIRECT_LLM_PRIMARY,
)
from eval_context.brief_builder import EvaluationBrief, build_brief
from eval_context.context_slicer import slice_context_for_agent, truncate_brief
from llm_utils import (
    get_model_name,
    invoke_direct_llm,
    invoke_with_retry,
    is_crew_abort_output,
)
from logging_config import get_logger, timed_operation
from progress import agent_complete, agent_start
from scoring.score_engine import build_evidence_profile, compute_overall, detect_contradictions, format_cross_exam
from tasks.evaluation_tasks import (
    create_chief_evaluation_task,
    create_narrative_task,
    create_innovation_task,
    create_presentation_task,
    create_risk_task,
    create_security_task,
    create_technical_task,
)
from validation.json_utils import log_raw_output, parse_agent_json, validate_chief_verdict
from validation.schemas import (
    InnovationReport,
    PresentationReport,
    RiskReport,
    SecurityReport,
    TechnicalReport,
)

logger = get_logger(__name__)
_executor = ThreadPoolExecutor(max_workers=max(1, OLLAMA_PARALLEL))

FALLBACKS: dict[str, dict[str, Any]] = {
    "technical": {
        "technical_score": FAILED_AGENT_SCORE,
        "strengths": [],
        "weaknesses": ["Engineering agent failed — manual technical review required"],
        "risks": ["Incomplete automated technical assessment"],
        "confidence": 0.15,
    },
    "security": {
        "security_score": FAILED_AGENT_SCORE,
        "risk_level": "MEDIUM",
        "critical_findings": ["Security agent failed — run manual security audit"],
        "confidence": 0.15,
    },
    "innovation": {
        "innovation_score": FAILED_AGENT_SCORE,
        "scalability_score": FAILED_AGENT_SCORE,
        "differentiators": [],
        "scalability_risk": "Unable to assess — agent failure",
        "confidence": 0.15,
    },
    "presentation": {
        "presentation_score": FAILED_AGENT_SCORE,
        "strengths": [],
        "improvements": ["Presentation agent failed — provide deck for manual review"],
        "confidence": 0.15,
        "status": "FAILED",
    },
    "risk": {
        "impact_score": FAILED_AGENT_SCORE,
        "failure_modes": ["Risk agent failed — insufficient automated assessment"],
        "top_risks": ["Manual risk review required"],
        "confidence": 0.15,
    },
}


def _agent_system_prompt(agent: Agent) -> str:
    return f"{agent.role}\nGoal: {agent.goal}\n{agent.backstory or ''}"


def _run_crew_kickoff(agent: Agent, task: Task) -> str:
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=False,
        max_rpm=0,
    )
    t0 = time.perf_counter()
    logger.info("Crew kickoff start agent=%s", getattr(agent, "role", "unknown"))
    result = crew.kickoff()
    elapsed = time.perf_counter() - t0
    raw = str(result.raw if hasattr(result, "raw") else result)
    logger.info(
        "Crew kickoff end agent=%s in %.2fs response_chars=%d",
        getattr(agent, "role", "unknown"),
        elapsed,
        len(raw),
    )
    return raw


def _run_agent_llm(
    *,
    agent: Agent,
    task: Task,
    role: str,
    label: str,
    project_id: str,
    use_fallback: bool = False,
) -> str:
    """Run specialist/chief: direct Ollama (default) or CrewAI with direct retry on abort."""
    system_prompt = _agent_system_prompt(agent)
    user_prompt = task.description or ""
    prompt_chars = len(system_prompt) + len(user_prompt)

    logger.info(
        "[%s] %s agent_start prompt_chars=%d digest_in_task=yes",
        project_id[:8],
        label,
        prompt_chars,
    )

    if USE_DIRECT_LLM_PRIMARY:
        raw = invoke_direct_llm(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            label=label,
            project_id=project_id,
            use_fallback=use_fallback,
        )
        if not is_crew_abort_output(raw):
            return raw
        logger.warning(
            "[%s] %s direct LLM returned abort-like output — retrying via CrewAI",
            project_id[:8],
            label,
        )

    raw = _run_crew_kickoff(agent, task)
    if is_crew_abort_output(raw):
        logger.error(
            "[%s] %s CrewAI aborted (iteration/time limit). Raw=%r — forcing direct LLM",
            project_id[:8],
            label,
            raw[:200],
        )
        raw = invoke_direct_llm(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            label=f"{label}:direct_recovery",
            project_id=project_id,
            use_fallback=use_fallback,
        )
        if is_crew_abort_output(raw):
            raise RuntimeError(
                f"{label} failed after CrewAI abort and direct LLM recovery: {raw[:300]}"
            )
    return raw


def _run_specialist(
    name: str,
    agent_factory: Callable,
    task_factory: Callable,
    brief_text: str,
    ctx: dict,
    model_cls,
    project_id: str,
):
    profile = AGENT_MODEL_PROFILES.get(name, "specialist")
    model_name = get_model_name(profile)
    start = time.perf_counter()

    agent_start(
        project_id,
        name,
        model=model_name,
        message=f"[{name.upper()}] Specialist review started",
    )

    parse_source = "fallback"
    brief_text = truncate_brief(brief_text)

    try:
        with timed_operation(
            logger,
            f"specialist:{name}",
            project_id=project_id,
            model=model_name,
        ):
            def _execute(*, use_fallback: bool = False) -> str:
                agent = agent_factory(use_fallback=use_fallback)
                digest = slice_context_for_agent(ctx, name)
                logger.info(
                    "[%s] %s context_digest_chars=%d brief_chars=%d",
                    project_id[:8],
                    name,
                    len(digest),
                    len(brief_text),
                )
                task = task_factory(agent, brief_text, digest)
                return _run_agent_llm(
                    agent=agent,
                    task=task,
                    role=profile,
                    label=f"specialist:{name}",
                    project_id=project_id,
                    use_fallback=use_fallback,
                )

            def _execute_fallback() -> str:
                fb_model = get_model_name(profile, use_fallback=True)
                logger.warning(
                    "[%s] %s retrying with fallback model %s",
                    project_id[:8],
                    name,
                    fb_model,
                )
                return _execute(use_fallback=True)

            raw = invoke_with_retry(
                lambda: _execute(use_fallback=False),
                fallback_fn=_execute_fallback,
                label=f"specialist:{name}",
                project_id=project_id,
                model=model_name,
            )

            log_raw_output(f"specialist:{name}", raw)
            t_parse = time.perf_counter()
            report, parse_source = parse_agent_json(
                raw,
                model_cls,
                FALLBACKS[name],
                label=f"specialist:{name}",
            )
            parse_sec = round(time.perf_counter() - t_parse, 2)
            logger.info(
                "[%s] %s json_validation duration=%.2fs source=%s",
                project_id[:8],
                name,
                parse_sec,
                parse_source,
            )

            duration = round(time.perf_counter() - start, 2)
            score_field = {
                "technical": "technical_score",
                "security": "security_score",
                "innovation": "innovation_score",
                "presentation": "presentation_score",
                "risk": "impact_score",
            }.get(name, "score")
            score_val = getattr(report, score_field, FAILED_AGENT_SCORE)

            msg = f"[{name.upper()}] Completed — raw_score={score_val}/100 ({duration}s) source={parse_source}"
            if parse_source != "llm":
                msg += " [parse degraded]"

            agent_complete(project_id, name, duration_sec=duration, message=msg)
            err = None if parse_source == "llm" else f"json_{parse_source}"
            return name, report, raw, err

    except Exception as exc:
        duration = round(time.perf_counter() - start, 2)
        logger.exception("[%s] Specialist %s failed: %s", project_id[:8], name, exc)
        report = model_cls(**FALLBACKS[name])
        agent_complete(
            project_id,
            name,
            duration_sec=duration,
            error=str(exc),
            message=f"[{name.upper()}] Failed — {exc}",
        )
        return name, report, json.dumps(FALLBACKS[name]), str(exc)


def _format_report_text(
    name: str,
    report: Any,
    raw: str,
    raw_scores: dict[str, int] | None = None,
    calibrated_scores: dict[str, int] | None = None,
    calibration_reasons: dict[str, list[str]] | None = None,
) -> str:
    if hasattr(report, "model_dump"):
        payload = report.model_dump()
        raw_scores = raw_scores or {}
        calibrated_scores = calibrated_scores or {}
        score_fields = {
            "technical": ("technical_score",),
            "security": ("security_score",),
            "innovation": ("innovation_score", "scalability_score"),
            "presentation": ("presentation_score",),
            "risk": ("impact_score",),
        }
        dimensions = {
            "technical": ("technical",), "security": ("security",),
            "innovation": ("innovation", "scalability"),
            "presentation": ("presentation",), "risk": ("impact",),
        }
        for field, dimension in zip(score_fields.get(name, ()), dimensions.get(name, ())):
            payload[field] = calibrated_scores.get(dimension, payload.get(field, 0))
        payload["raw_scores"] = {d: raw_scores.get(d, 0) for d in dimensions.get(name, ())}
        payload["calibrated_scores"] = {d: calibrated_scores.get(d, 0) for d in dimensions.get(name, ())}
        payload["calibration_reasons"] = {
            d: (calibration_reasons or {}).get(d, []) for d in dimensions.get(name, ())
        }
        return json.dumps(payload, indent=2)
    return raw


def run_evaluation(
    project_id: str,
    ctx: dict[str, Any],
    project_context_text: str | None = None,
) -> dict[str, Any]:
    eval_start = time.perf_counter()
    failures: dict[str, str] = {}

    agent_start(project_id, "coordinator", message="[COORDINATOR] Building evaluation brief")
    brief_start = time.perf_counter()
    brief: EvaluationBrief = build_brief(ctx)
    brief_text = truncate_brief(brief.to_text())
    agent_complete(
        project_id,
        "coordinator",
        duration_sec=round(time.perf_counter() - brief_start, 2),
        message=f"[COORDINATOR] Context brief ready ({len(brief_text)} chars)",
    )

    jobs = [
        ("technical", create_technical_agent, create_technical_task, TechnicalReport),
        ("security", create_security_agent, create_security_task, SecurityReport),
        ("presentation", create_presentation_agent, create_presentation_task, PresentationReport),
        ("innovation", create_innovation_agent, create_innovation_task, InnovationReport),
        ("risk", create_risk_agent, create_risk_task, RiskReport),
    ]

    reports: dict[str, Any] = {}
    raw_outputs: dict[str, str] = {}
    parse_sources: dict[str, str] = {}

    futures = {
        _executor.submit(
            _run_specialist,
            name,
            agent_factory,
            task_factory,
            brief_text,
            ctx,
            model_cls,
            project_id,
        ): name
        for name, agent_factory, task_factory, model_cls in jobs
    }

    try:
        completed = as_completed(futures, timeout=EVALUATION_TIMEOUT_SEC)
        for future in completed:
            name, report, raw, err = future.result(timeout=AGENT_TIMEOUT_SEC)
            reports[name] = report
            raw_outputs[name] = raw
            parse_sources[name] = "llm" if not err else "fallback"
            if err:
                failures[name] = err
    except TimeoutError:
        logger.error("[%s] Evaluation pool timed out after %ds", project_id[:8], EVALUATION_TIMEOUT_SEC)
        for future, name in futures.items():
            if name not in reports:
                model_cls = next(m for n, _, _, m in jobs if n == name)
                reports[name] = model_cls(**FALLBACKS[name])
                raw_outputs[name] = json.dumps(FALLBACKS[name])
                failures[name] = "pool timeout"
                parse_sources[name] = "fallback"
                agent_complete(
                    project_id,
                    name,
                    error="pool timeout",
                    message=f"[{name.upper()}] Pool timeout — fallback score={FAILED_AGENT_SCORE}",
                )

    technical: TechnicalReport = reports["technical"]
    security: SecurityReport = reports["security"]
    innovation: InnovationReport = reports["innovation"]
    presentation: PresentationReport = reports["presentation"]
    risk: RiskReport = reports["risk"]

    scoring_start = time.perf_counter()
    agent_start(project_id, "scoring", message="[SCORE] Computing weighted verdict")
    evidence = build_evidence_profile(ctx, parse_sources)
    computed = compute_overall(
        technical, security, innovation, presentation, risk,
        project_type=ctx.get("project_type", "Hackathon Project"),
        evidence=evidence,
    )
    contradictions = detect_contradictions(
        technical, security, innovation, presentation, risk, brief.missing
    )
    computed["contradictions"] = contradictions
    computed["executive_summary"] = _build_executive_summary(computed, contradictions, failures)
    computed["deployment_roadmap"] = _build_roadmap(computed, failures)
    computed["recommended_fixes"] = list(computed.get("top_weaknesses", []))[:5]
    agent_complete(
        project_id,
        "scoring",
        duration_sec=round(time.perf_counter() - scoring_start, 2),
        message=f"[SCORE] Overall={computed['overall_score']}/100 verdict={computed['verdict']}",
    )

    specialist_summary = json.dumps(
        {
            "technical": technical.model_dump(),
            "security": security.model_dump(),
            "innovation": innovation.model_dump(),
            "presentation": presentation.model_dump(),
            "risk": risk.model_dump(),
            "failures": failures,
            "contradictions": contradictions,
        },
        indent=2,
    )[:3500]

    # Compute deterministic numeric verdict and pass only numeric summary to chief for narrative synthesis
    # Narrative agent synthesizes qualitative narrative only (scores already computed)
    narrative_model = get_model_name("chief")
    narrative_start = time.perf_counter()
    agent_start(
        project_id,
        "narrative",
        model=narrative_model,
        message="[NARRATIVE] Generating narrative from computed scores",
    )

    numeric_payload = {
        k: computed[k]
        for k in ("overall_score", "verdict", "risk_level", "agent_scores")
        if k in computed
    }

    # key findings: short cross-exam or top lines from specialists
    key_findings = " | ".join((technical.strengths or [])[:2] + (security.critical_findings or [])[:2] + (innovation.differentiators or [])[:2])

    narrative_agent = create_narrative_agent()
    narrative_task = create_narrative_task(narrative_agent, numeric_payload, key_findings)

    narrative_raw = ""
    narrative_parse_source = "computed"
    try:
        with timed_operation(
            logger,
            "narrative:gen",
            project_id=project_id,
            model=narrative_model,
        ):
            narrative_raw = _run_agent_llm(
                agent=narrative_agent,
                task=narrative_task,
                role="chief",
                label="narrative:gen",
                project_id=project_id,
                use_fallback=False,
            )
            if not narrative_raw or len(narrative_raw.strip()) == 0:
                raise RuntimeError("Narrative agent returned empty response")
            narrative_parse_source = "llm"
    except Exception as exc:
        logger.exception("[%s] Narrative agent failed — using computed fallback narrative", project_id[:8])
        failures["narrative"] = str(exc)
        narrative_raw = json.dumps(
            {
                "executive_summary": "Evaluation completed successfully. Narrative generation unavailable.",
                "top_strengths": computed.get("top_strengths", []),
                "top_weaknesses": computed.get("top_weaknesses", []),
                "recommended_fixes": computed.get("recommended_fixes", []),
                "deployment_roadmap": computed.get("deployment_roadmap", []),
            }
        )
        narrative_parse_source = "computed"

    verdict_start = time.perf_counter()
    # Validate and merge narrative output into computed verdict structure
    log_raw_output("narrative:gen", narrative_raw)
    # Narrative should not modify computed numeric fields — validate_chief_verdict enforces numeric values
    verdict, narrative_parse_source = validate_chief_verdict(
        narrative_raw, computed, label="narrative:gen"
    )
    logger.info(
        "[%s] narrative json_validation duration=%.2fs source=%s",
        project_id[:8],
        time.perf_counter() - narrative_start,
        narrative_parse_source,
    )
    verdict_dict = verdict.model_dump()
    narrative_duration = round(time.perf_counter() - narrative_start, 2)

    if narrative_parse_source != "llm":
        failures["narrative_parse"] = narrative_parse_source

    agent_complete(
        project_id,
        "narrative",
        duration_sec=narrative_duration,
        error=failures.get("narrative"),
        message=(
            f"[NARRATIVE] Verdict={verdict_dict['verdict']} "
            f"score={verdict_dict['overall_score']}/100 source={narrative_parse_source}"
        ),
    )

    total_elapsed = round(time.perf_counter() - eval_start, 2)
    logger.info(
        "[%s] Evaluation complete in %.2fs — verdict=%s score=%d failures=%s",
        project_id[:8],
        total_elapsed,
        verdict_dict["verdict"],
        verdict_dict["overall_score"],
        list(failures.keys()) or "none",
    )

    cross_exam = format_cross_exam(contradictions)
    raw_score_map = computed["raw_agent_scores"]
    calibrated_score_map = computed["calibrated_agent_scores"]
    calibration_reasons = computed["agent_calibration_reasons"]

    return {
        "brief": brief_text,
        "technical": _format_report_text("technical", technical, raw_outputs["technical"], raw_score_map, calibrated_score_map, calibration_reasons),
        "security": _format_report_text("security", security, raw_outputs["security"], raw_score_map, calibrated_score_map, calibration_reasons),
        "innovation": _format_report_text("innovation", innovation, raw_outputs["innovation"], raw_score_map, calibrated_score_map, calibration_reasons),
        "presentation": _format_report_text("presentation", presentation, raw_outputs["presentation"], raw_score_map, calibrated_score_map, calibration_reasons),
        "risk": _format_report_text("risk", risk, raw_outputs["risk"], raw_score_map, calibrated_score_map, calibration_reasons),
        "ppt": _format_report_text("presentation", presentation, raw_outputs["presentation"], raw_score_map, calibrated_score_map, calibration_reasons),
        "impact": json.dumps(
            {"impact_score": calibrated_score_map["impact"], "raw_impact_score": raw_score_map["impact"], "top_risks": risk.top_risks},
            indent=2,
        ),
        "failure": "\n".join(f"- {m}" for m in risk.failure_modes),
        "scalability": json.dumps(
            {
                "scalability_score": calibrated_score_map["scalability"],
                "raw_scalability_score": raw_score_map["scalability"],
                "scalability_risk": innovation.scalability_risk,
            },
            indent=2,
        ),
        "cross_exam": cross_exam,
        "chief_evaluation": json.dumps(verdict_dict, indent=2),
        "verdict": verdict_dict,
        "raw_verdict": narrative_raw,
        "raw_agent_outputs": raw_outputs,
        "raw_agent_scores": raw_score_map,
        "calibrated_agent_scores": calibrated_score_map,
        "agent_failures": failures,
        "evaluation_duration_sec": total_elapsed,
        "engineering": raw_outputs["technical"],
        "innovation_scalability": raw_outputs["innovation"],
        "risk_impact": raw_outputs["risk"],
        "coordination": brief_text,
    }


def _build_executive_summary(
    computed: dict[str, Any],
    contradictions: list[str],
    failures: dict[str, str],
) -> str:
    verdict = computed["verdict"]
    score = computed["overall_score"]
    risk = computed.get("risk_level", "MEDIUM")
    parts = [
        f"Deployment readiness score: {score}/100 with {verdict} recommendation.",
        f"Risk level assessed as {risk}.",
    ]
    strengths = computed.get("top_strengths", [])
    if strengths:
        parts.append(f"Key strength: {strengths[0]}.")
    weaknesses = computed.get("top_weaknesses", [])
    if weaknesses:
        parts.append(f"Primary concern: {weaknesses[0]}.")
    if contradictions:
        parts.append(f"Cross-exam flagged {len(contradictions)} contradiction(s) requiring review.")
    if failures:
        parts.append(f"Degraded agents: {', '.join(failures.keys())}.")
    return " ".join(parts)


def _build_roadmap(computed: dict[str, Any], failures: dict[str, str]) -> list[str]:
    verdict = computed["verdict"]
    blocking = computed.get("blocking_issues", [])

    if verdict == "ACCEPT":
        roadmap = [
            "Phase 1: Final security scan and staging deployment",
            "Phase 2: Load testing and observability setup",
            "Phase 3: Production rollout with canary release",
        ]
    elif verdict == "IMPROVE":
        roadmap = [
            "Phase 1: Address blocking issues and re-run evaluation",
            "Phase 2: Staged deployment with monitoring",
            "Phase 3: Production after validation gates pass",
        ]
    else:
        roadmap = [
            "Phase 1: Resolve critical blockers before any deployment",
            "Phase 2: Re-architecture review with engineering team",
            "Phase 3: Re-submit for full Sentinel evaluation",
        ]

    for issue in blocking[:2]:
        roadmap.insert(0, f"Blocker: {issue}")
    if failures:
        roadmap.append(f"Re-run failed agents: {', '.join(failures.keys())}")
    return roadmap[:6]
