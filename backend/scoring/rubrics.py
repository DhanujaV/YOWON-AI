"""Project-type rubrics and scoring configuration."""

from __future__ import annotations

from typing import Any

DEFAULT_PROJECT_TYPE = "Hackathon Project"
PROJECT_TYPES = (
    "University Project", "Hackathon Project", "Startup Pitch",
    "Research Project", "Corporate Project", "Open Source Project",
)

RUBRICS: dict[str, dict[str, Any]] = {
    "University Project": {
        "standard": "Academic quality, learning outcomes, correctness, and clear communication",
        "focus": ["technical correctness", "academic rigor", "innovation", "presentation"],
        "avoid_expectations": ["Kubernetes", "CI/CD", "enterprise security", "large-scale deployment"],
        "weights": {"technical": .30, "presentation": .25, "innovation": .20, "risk": .15, "security": .10},
        "bands": {90: "Exceptional academic project", 80: "Excellent", 70: "Good", 60: "Average", 0: "Needs improvement"},
    },
    "Hackathon Project": {
        "standard": "Prototype quality, innovation, demo readiness, and execution under time constraints",
        "focus": ["innovation", "prototype quality", "demo readiness"],
        "avoid_expectations": ["production-scale operations", "complete compliance program"],
        "weights": {"innovation": .35, "technical": .25, "presentation": .20, "risk": .10, "security": .10},
        "bands": {90: "Exceptional hackathon project", 80: "Strong finalist", 70: "Competitive prototype", 60: "Promising prototype", 0: "Needs improvement"},
    },
    "Startup Pitch": {
        "standard": "Market viability, business model, differentiation, evidence, and execution risk",
        "focus": ["market viability", "business model", "product differentiation", "execution risk"],
        "avoid_expectations": ["enterprise operations before product-market evidence"],
        "weights": {"innovation": .25, "technical": .20, "presentation": .15, "risk": .20, "business_feasibility": .20},
        "bands": {90: "Exceptional investment-ready pitch", 80: "Strong opportunity", 70: "Promising with validation gaps", 60: "Early concept", 0: "Needs major validation"},
    },
    "Research Project": {
        "standard": "Research novelty, academic contribution, experimental rigor, reproducibility, baseline benchmarking, and publication potential",
        "focus": [
            "novelty", "research contribution", "experimental rigor",
            "reproducibility", "baseline benchmarking", "publication potential",
        ],
        "avoid_expectations": ["commercial deployment unless claimed", "large code volume", "UI polish"],
        "weights": {"innovation": .35, "technical": .25, "impact": .25, "presentation": .10, "security": .03, "scalability": .02},
        "bands": {90: "Publication-grade contribution", 80: "Strong research project", 70: "Sound with revision needed", 60: "Preliminary study", 0: "Methodology needs improvement"},
    },
    "Corporate Project": {
        "standard": "Production readiness, security, scalability, compliance, reliability, and maintainability",
        "focus": ["security", "scalability", "compliance", "reliability", "maintainability"],
        "avoid_expectations": [],
        "weights": {"technical": .30, "security": .30, "risk": .20, "innovation": .05, "presentation": .15},
        "bands": {90: "Production-ready", 80: "Strong", 70: "Needs improvements", 0: "Not deployment ready"},
    },
    "Open Source Project": {
        "standard": "Documentation, community readiness, code quality, maintainability, and contributor experience",
        "focus": ["documentation", "community readiness", "code quality", "maintainability"],
        "avoid_expectations": ["enterprise compliance unless claimed"],
        "weights": {"technical": .30, "presentation": .20, "innovation": .15, "security": .15, "impact": .10, "scalability": .10},
        "bands": {90: "Exceptional community-ready project", 80: "Strong open source project", 70: "Useful with maintenance gaps", 60: "Early-stage project", 0: "Needs improvement"},
    },
}


def normalize_project_type(project_type: str | None) -> str:
    return project_type if project_type in RUBRICS else DEFAULT_PROJECT_TYPE


def get_rubric(project_type: str | None) -> dict[str, Any]:
    normalized = normalize_project_type(project_type)
    return {"project_type": normalized, **RUBRICS[normalized]}


def rubric_prompt(project_type: str | None) -> str:
    rubric = get_rubric(project_type)
    weights = ", ".join(f"{k}={int(v * 100)}%" for k, v in rubric["weights"].items())
    avoid = ", ".join(rubric["avoid_expectations"]) or "none"
    research_rules = ""
    if rubric["project_type"] == "Research Project":
        research_rules = (
            "\nRESEARCH_EVIDENCE_REQUIRED: baseline comparison, experimental results, "
            "novel contribution, reproducibility details, and publication potential. "
            "Do not reward code volume, deployment readiness, or UI polish as substitutes."
        )
    return (
        f"PROJECT_TYPE: {rubric['project_type']}\nEVALUATION_STANDARD: {rubric['standard']}\n"
        f"FOCUS: {', '.join(rubric['focus'])}\nDO_NOT_EXPECT: {avoid}\nSCORING_WEIGHTS: {weights}\n"
        "Judge only against this context. Scores above 90 require exceptional explicit evidence."
        f"{research_rules}"
    )
