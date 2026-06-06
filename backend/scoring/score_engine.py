"""Context-aware deterministic scoring and measurable confidence."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from scoring.rubrics import get_rubric
from validation.schemas import (
    AgentScores, InnovationReport, PresentationReport, RiskReport,
    SecurityReport, TechnicalReport,
)

DIMENSIONS = ("technical", "security", "scalability", "innovation", "presentation", "impact")


def build_evidence_profile(ctx: dict[str, Any], parse_sources: dict[str, str] | None = None) -> dict[str, Any]:
    gh, sec = ctx.get("github") or {}, ctx.get("security") or {}
    structure_items = gh.get("folder_structure") or []
    structure = " ".join(structure_items).lower()
    readme = gh.get("readme") or ""
    description = ctx.get("description") or ""
    pdf_text = ((ctx.get("pdf") or {}).get("full_text") or "")
    ppt_text = ((ctx.get("ppt") or {}).get("full_text") or "")
    evidence_text = " ".join((description, readme, pdf_text, ppt_text)).lower()
    has_repo = bool(gh and not gh.get("error"))
    repository_has_content = has_repo and bool(
        structure_items or gh.get("dependencies") or gh.get("python_files")
        or (readme and readme != "[No README found]")
    )

    checks = {
        "documentation": bool(len(readme) > 120 or ctx.get("pdf") or ctx.get("ppt")),
        "tests": repository_has_content and any(x in structure for x in ("test", "spec", "__tests__")),
        "deployment": repository_has_content and any(x in structure for x in ("dockerfile", "deploy", ".github", "kubernetes", "terraform")),
        "security_practices": bool(sec) and not sec.get("secret_findings"),
        "innovation_evidence": len(description) > 120 or bool(gh.get("topics")),
        "baseline_comparison": any(x in evidence_text for x in ("baseline", "benchmark", "compared with", "comparison")),
        "experimental_evidence": any(x in evidence_text for x in ("experiment", "results", "accuracy", "precision", "recall", "f1", "dataset", "evaluation")),
        "novelty_evidence": any(x in evidence_text for x in ("novel", "novelty", "contribution", "literature gap", "original")),
        "reproducibility": any(x in evidence_text for x in ("reproduc", "seed", "methodology", "method", "notebook", "environment")),
        "market_evidence": any(x in evidence_text for x in ("market", "customer", "revenue", "business model", "validation")),
    }
    available = sum((repository_has_content, bool(description), bool(ctx.get("pdf")), bool(ctx.get("ppt")), bool(sec)))
    repository_coverage = min(
        100,
        (35 if repository_has_content else 0)
        + min(40, len(structure_items) // 2)
        + min(25, len(gh.get("python_files") or []) * 5),
    )
    sources = parse_sources or {}
    json_validity = round(100 * sum(v == "llm" for v in sources.values()) / len(sources)) if sources else 100
    return {
        "checks": checks,
        "has_repository": has_repo,
        "repository_has_content": repository_has_content,
        "empty_repository": has_repo and not repository_has_content,
        "data_availability": round(available / 5 * 100),
        "repository_coverage": repository_coverage,
        "json_validity": json_validity,
    }


def calibrate_agent_scores(
    raw_scores: dict[str, int],
    evidence: dict[str, Any],
    project_type: str,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Calibrate each public specialist score using evidence available to that specialist."""
    scores = {key: max(0, min(100, int(raw_scores.get(key, 0)))) for key in DIMENSIONS}
    reasons: dict[str, list[str]] = {key: [] for key in DIMENSIONS}
    checks = evidence.get("checks", {})

    def deduct(dimension: str, points: int, reason: str) -> None:
        scores[dimension] = max(0, scores[dimension] - points)
        reasons[dimension].append(reason)

    def cap(dimension: str, maximum: int, reason: str) -> None:
        if scores[dimension] > maximum:
            scores[dimension] = maximum
            reasons[dimension].append(reason)

    if evidence.get("empty_repository") or (
        not evidence.get("repository_has_content") and evidence.get("data_availability", 0) <= 20
    ):
        for dimension in ("technical", "security", "scalability", "presentation", "impact"):
            cap(dimension, 20, "Insufficient evidence: repository is empty")
        cap("innovation", 10, "Insufficient evidence: repository is empty")
        return scores, reasons

    if not evidence.get("repository_has_content"):
        cap("technical", 35, "No substantive repository evidence")
        cap("security", 35, "No substantive repository evidence")
        cap("scalability", 35, "No substantive repository evidence")
    if not checks.get("tests"):
        deduct("technical", 8, "No test evidence")
    if not checks.get("security_practices"):
        deduct("security", 12, "No security-practice evidence")
    if not checks.get("documentation"):
        deduct("presentation", 25, "No documentation or presentation evidence")
    if not checks.get("innovation_evidence"):
        deduct("innovation", 18, "No innovation evidence")
    if evidence.get("data_availability", 0) < 40:
        cap("impact", 40, "Insufficient evidence to substantiate impact")

    if project_type == "Research Project":
        research_penalties = (
            ("baseline_comparison", "technical", 10, "No baseline comparison"),
            ("experimental_evidence", "technical", 15, "No experimental evidence"),
            ("experimental_evidence", "impact", 12, "No experimental evidence"),
            ("novelty_evidence", "innovation", 22, "No novelty evidence"),
            ("novelty_evidence", "impact", 10, "No research contribution evidence"),
            ("reproducibility", "technical", 12, "No reproducibility information"),
            ("reproducibility", "presentation", 8, "No reproducibility information"),
        )
        for check, dimension, points, reason in research_penalties:
            if not checks.get(check):
                deduct(dimension, points, reason)
        # Research is judged on evidence quality, not repository size or polished UI.
        if checks.get("experimental_evidence") and checks.get("reproducibility"):
            scores["technical"] = min(100, scores["technical"] + 5)
        if checks.get("novelty_evidence") and checks.get("baseline_comparison"):
            scores["innovation"] = min(100, scores["innovation"] + 5)

    if project_type == "Startup Pitch" and not checks.get("market_evidence"):
        deduct("impact", 28, "No market or customer validation evidence")
        deduct("presentation", 15, "No business model evidence")
    if project_type == "Corporate Project":
        if not checks.get("deployment"):
            deduct("technical", 19, "No deployment evidence")
            deduct("scalability", 15, "No deployment evidence")
            deduct("security", 15, "No compliance or deployment-security evidence")
            deduct("impact", 15, "No production-readiness evidence")
        if not checks.get("tests"):
            deduct("technical", 7, "Corporate reliability evidence missing")

    return scores, reasons


def compute_overall(
    technical: TechnicalReport, security: SecurityReport, innovation: InnovationReport,
    presentation: PresentationReport, risk: RiskReport, *, project_type: str = "Hackathon Project",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rubric = get_rubric(project_type)
    raw_scores = AgentScores(
        technical=technical.technical_score, security=security.security_score,
        scalability=innovation.scalability_score, innovation=innovation.innovation_score,
        presentation=presentation.presentation_score, impact=risk.impact_score,
    ).model_dump()
    raw_scores = {k: max(0, min(100, int(v))) for k, v in raw_scores.items()}
    evidence = evidence or {"checks": {}, "data_availability": 0, "repository_coverage": 0, "json_validity": 0}
    calibrated_scores, calibration_reasons = calibrate_agent_scores(
        raw_scores, evidence, rubric["project_type"]
    )
    scoring_inputs = {
        **calibrated_scores,
        "risk": calibrated_scores["impact"],
        "business_feasibility": calibrated_scores["impact"],
    }
    weighted_score = round(sum(scoring_inputs[k] * weight for k, weight in rubric["weights"].items()))

    penalties = [
        {"factor": reason, "dimension": dimension}
        for dimension, items in calibration_reasons.items() for reason in items
    ]
    overall = weighted_score
    if overall > 89 and (evidence.get("data_availability", 0) < 80 or penalties):
        penalties.append({"factor": "Exceptional-score evidence gate", "dimension": "overall"})
        overall = 89
    if security.risk_level == "CRITICAL" or calibrated_scores["security"] < 20:
        overall = min(overall, 40)

    overall = round(max(0, overall))
    label = next(label for threshold, label in rubric["bands"].items() if overall >= threshold)
    confidence = _confidence(calibrated_scores, evidence)
    strengths = [f"Strong {k} ({v}/100)" for k, v in calibrated_scores.items() if v >= 80][:5]
    weaknesses = [f"Weak {k} ({v}/100)" for k, v in calibrated_scores.items() if v < 60][:5]
    missing = list(dict.fromkeys(p["factor"] for p in penalties if p["factor"].startswith(("No ", "Insufficient"))))

    return {
        "overall_score": overall, "raw_weighted_score": round(sum(
            ({**raw_scores, "risk": raw_scores["impact"], "business_feasibility": raw_scores["impact"]})[k] * w
            for k, w in rubric["weights"].items()
        )),
        "verdict": _verdict(overall, rubric["project_type"]),
        "risk_level": _infer_risk_level(security, calibrated_scores["security"], overall),
        "agent_scores": calibrated_scores,  # Backward-compatible public alias.
        "raw_agent_scores": raw_scores, "calibrated_agent_scores": calibrated_scores,
        "agent_calibration_reasons": calibration_reasons,
        "project_type": rubric["project_type"], "evaluation_standard": rubric["standard"],
        "scoring_weights": rubric["weights"], "score_band": label, "confidence": confidence,
        "penalties": penalties, "missing_evidence": missing, "positive_factors": strengths,
        "blocking_issues": security.critical_findings[:3] if security.risk_level in ("HIGH", "CRITICAL") else [],
        "top_strengths": strengths, "top_weaknesses": (weaknesses + missing)[:5],
    }


def _confidence(agent_map: dict[str, int], evidence: dict[str, Any]) -> int:
    agreement = max(0, 100 - round(pstdev(agent_map.values()) * 2.5))
    checks = evidence.get("checks", {})
    completeness = round(sum(bool(v) for v in checks.values()) / max(1, len(checks)) * 100)
    return round(
        agreement * .30 + completeness * .25 + evidence.get("data_availability", 0) * .20
        + evidence.get("json_validity", 0) * .15 + evidence.get("repository_coverage", 0) * .10
    )


def _verdict(score: int, project_type: str) -> str:
    if project_type == "Corporate Project":
        return "ACCEPT" if score >= 90 else "CONDITIONAL_APPROVE" if score >= 80 else "IMPROVE" if score >= 70 else "REJECT"
    return "ACCEPT" if score >= 85 else "CONDITIONAL_APPROVE" if score >= 70 else "IMPROVE" if score >= 50 else "REJECT"


def _infer_risk_level(security: SecurityReport, calibrated_security: int, overall: int) -> str:
    if security.risk_level == "CRITICAL" or calibrated_security < 20: return "CRITICAL"
    if security.risk_level == "HIGH" or overall < 50: return "HIGH"
    if overall < 75: return "MEDIUM"
    return "LOW"


def detect_contradictions(technical, security, innovation, presentation, risk, brief_missing):
    out = []
    if technical.technical_score > 80 and security.security_score < 50: out.append("High technical score conflicts with low security score")
    if presentation.presentation_score > 80 and brief_missing: out.append("High presentation score despite missing materials")
    if innovation.innovation_score > 85 and innovation.confidence < .5: out.append("High innovation score with low confidence")
    if risk.impact_score > 75 and len(risk.top_risks) >= 4: out.append("Strong impact score despite multiple material risks")
    return out


def format_cross_exam(contradictions: list[str]) -> str:
    return "No major contradictions detected across specialist agents." if not contradictions else "CONTRADICTIONS:\n" + "\n".join(f"- {c}" for c in contradictions)
