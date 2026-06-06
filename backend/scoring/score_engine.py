"""Context-aware deterministic scoring and measurable confidence."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from scoring.rubrics import get_rubric
from validation.schemas import (
    AgentScores, InnovationReport, PresentationReport, RiskReport,
    SecurityReport, TechnicalReport,
)


def build_evidence_profile(ctx: dict[str, Any], parse_sources: dict[str, str] | None = None) -> dict[str, Any]:
    gh, sec = ctx.get("github") or {}, ctx.get("security") or {}
    structure = " ".join(gh.get("folder_structure") or []).lower()
    readme = gh.get("readme") or ""
    description = ctx.get("description") or ""
    has_repo = bool(gh and not gh.get("error"))
    checks = {
        "documentation": bool(len(readme) > 120 or ctx.get("pdf") or ctx.get("ppt")),
        "tests": has_repo and any(x in structure for x in ("test", "spec", "__tests__")),
        "deployment": has_repo and any(x in structure for x in ("dockerfile", "deploy", ".github", "kubernetes", "terraform")),
        "security_practices": bool(sec) and not sec.get("secret_findings"),
        "innovation_evidence": len(description) > 120 or bool(gh.get("topics")),
    }
    available = sum((has_repo, bool(description), bool(ctx.get("pdf")), bool(ctx.get("ppt")), bool(sec)))
    repository_coverage = min(100, (35 if has_repo else 0) + min(40, len(gh.get("folder_structure") or []) // 2) + min(25, len(gh.get("python_files") or []) * 5))
    sources = parse_sources or {}
    json_validity = round(100 * sum(v == "llm" for v in sources.values()) / len(sources)) if sources else 100
    return {
        "checks": checks,
        "data_availability": round(available / 5 * 100),
        "repository_coverage": repository_coverage,
        "json_validity": json_validity,
    }


def compute_overall(
    technical: TechnicalReport, security: SecurityReport, innovation: InnovationReport,
    presentation: PresentationReport, risk: RiskReport, *, project_type: str = "Hackathon Project",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rubric = get_rubric(project_type)
    scores = AgentScores(
        technical=technical.technical_score, security=security.security_score,
        scalability=innovation.scalability_score, innovation=innovation.innovation_score,
        presentation=presentation.presentation_score, impact=risk.impact_score,
    ).model_dump()
    agent_map = {k: max(0, min(100, int(v))) for k, v in scores.items()}
    scoring_inputs = {**agent_map, "risk": agent_map["impact"], "business_feasibility": agent_map["impact"]}
    weights = rubric["weights"]
    weighted_score = round(sum(scoring_inputs[k] * weight for k, weight in weights.items()))

    evidence = evidence or {"checks": {}, "data_availability": 0, "repository_coverage": 0, "json_validity": 0}
    penalty_values = {
        "documentation": 8, "tests": 7, "deployment": 6,
        "security_practices": 8, "innovation_evidence": 6,
    }
    applicable = set(penalty_values)
    if rubric["project_type"] in ("University Project", "Hackathon Project", "Research Project"):
        applicable.discard("deployment")
    if rubric["project_type"] == "University Project":
        penalty_values["security_practices"] = 3
    penalties = [
        {"factor": f"Missing {name.replace('_', ' ')}", "points": penalty_values[name]}
        for name in applicable if not evidence.get("checks", {}).get(name, False)
    ]
    calibrated = max(0, weighted_score - sum(p["points"] for p in penalties))

    # Exceptional scores require broad evidence, not merely optimistic agent output.
    if calibrated > 89 and (evidence.get("data_availability", 0) < 80 or len(penalties) > 0):
        penalties.append({"factor": "Exceptional-score evidence gate", "points": calibrated - 89})
        calibrated = 89
    if security.risk_level == "CRITICAL" or agent_map["security"] < 40:
        calibrated = min(calibrated, 40)

    overall = round(calibrated)
    label = next(label for threshold, label in rubric["bands"].items() if overall >= threshold)
    verdict = _verdict(overall, rubric["project_type"])
    confidence = _confidence(agent_map, evidence)
    strengths = [f"Strong {k} ({v}/100)" for k, v in agent_map.items() if v >= 80][:5]
    weaknesses = [f"Weak {k} ({v}/100)" for k, v in agent_map.items() if v < 60][:5]
    missing = [p["factor"] for p in penalties if p["factor"].startswith("Missing")]

    return {
        "overall_score": overall, "raw_weighted_score": weighted_score, "verdict": verdict,
        "risk_level": _infer_risk_level(security, overall), "agent_scores": agent_map,
        "project_type": rubric["project_type"], "evaluation_standard": rubric["standard"],
        "scoring_weights": weights, "score_band": label, "confidence": confidence,
        "penalties": penalties, "missing_evidence": missing,
        "positive_factors": strengths, "blocking_issues": security.critical_findings[:3] if security.risk_level in ("HIGH", "CRITICAL") else [],
        "top_strengths": strengths, "top_weaknesses": (weaknesses + missing)[:5],
    }


def _confidence(agent_map: dict[str, int], evidence: dict[str, Any]) -> int:
    agreement = max(0, 100 - round(pstdev(agent_map.values()) * 2.5))
    completeness = round(sum(evidence.get("checks", {}).values()) / 5 * 100)
    return round(
        agreement * .30 + completeness * .25 + evidence.get("data_availability", 0) * .20
        + evidence.get("json_validity", 0) * .15 + evidence.get("repository_coverage", 0) * .10
    )


def _verdict(score: int, project_type: str) -> str:
    if project_type == "Corporate Project":
        return "ACCEPT" if score >= 90 else "CONDITIONAL_APPROVE" if score >= 80 else "IMPROVE" if score >= 70 else "REJECT"
    return "ACCEPT" if score >= 85 else "CONDITIONAL_APPROVE" if score >= 70 else "IMPROVE" if score >= 50 else "REJECT"


def _infer_risk_level(security: SecurityReport, overall: int) -> str:
    if security.risk_level == "CRITICAL" or security.security_score < 35: return "CRITICAL"
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
