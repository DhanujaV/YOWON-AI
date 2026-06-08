"""JSON extraction and Pydantic validation for agent outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class AgentScoresModel(BaseModel):
    technical: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    scalability: int = Field(ge=0, le=100)
    innovation: int = Field(ge=0, le=100)
    presentation: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)


class ChiefVerdictModel(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    risk_level: str
    verdict: str
    executive_summary: str = ""
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    recommended_fixes: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)
    deployment_roadmap: list[str] = Field(default_factory=list)
    agent_scores: AgentScoresModel
    detected_technologies: list[str] = Field(default_factory=list)
    detected_algorithms: list[str] = Field(default_factory=list)
    architecture_summary: str = ""
    evidence_found: list[str] = Field(default_factory=list)
    evidence_missing: list[str] = Field(default_factory=list)
    calibration_explanation: str = ""
    project_type_justification: str = ""
    community_impact_score: int = 0


AGENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "technical": {
        "technical_score": 50,
        "strengths": ["Insufficient evidence for full assessment"],
        "weaknesses": ["Limited repository data"],
        "risks": ["Unknown architecture risks"],
        "confidence": 0.3,
    },
    "security": {
        "security_score": 50,
        "risk_level": "MEDIUM",
        "critical_findings": [],
        "recommendations": ["Run full security audit"],
        "confidence": 0.3,
    },
    "innovation": {
        "innovation_score": 50,
        "scalability_score": 50,
        "differentiators": [],
        "competitors": [],
        "scalability_risk": "Unknown scaling constraints",
        "confidence": 0.3,
    },
    "presentation": {
        "presentation_score": 50,
        "strengths": [],
        "improvements": ["Add pitch deck or documentation"],
        "has_deck": False,
        "confidence": 0.3,
    },
    "risk": {
        "impact_score": 50,
        "failure_modes": ["Insufficient data for failure analysis"],
        "risks": ["Deployment risks not fully assessed"],
        "risk_level": "MEDIUM",
        "confidence": 0.3,
    },
}


def extract_json(text: str) -> dict[str, Any]:
    if not text:
        return {}

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    for candidate in (cleaned,):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def _extract_score_from_text(text: str, label: str) -> int | None:
    pattern = rf"{label}\s*[:=]\s*(\d{{1,3}})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return max(0, min(100, int(match.group(1))))
    return None


def parse_agent_report(agent_key: str, raw: str) -> dict[str, Any]:
    defaults = dict(AGENT_DEFAULTS.get(agent_key, {"score": 50, "confidence": 0.3}))
    data = extract_json(raw)
    if data:
        merged = {**defaults, **data}
        return merged

    # Legacy free-text fallback
    merged = dict(defaults)
    score_map = {
        "technical": "TECHNICAL SCORE",
        "security": "SECURITY SCORE",
        "innovation": "INNOVATION SCORE",
        "presentation": "PRESENTATION SCORE",
        "risk": "IMPACT SCORE",
    }
    label = score_map.get(agent_key)
    if label:
        score = _extract_score_from_text(raw, label)
        if score is not None:
            merged[f"{agent_key}_score"] = score
    if agent_key == "innovation":
        sc = _extract_score_from_text(raw, "SCALABILITY SCORE")
        if sc is not None:
            merged["scalability_score"] = sc

    merged["_raw_text"] = raw[:2000]
    return merged


def validate_chief_verdict(raw: str, computed: dict[str, Any]) -> dict[str, Any]:
    data = extract_json(raw)
    if not data:
        return merge_chief_verdict({}, computed)

    try:
        model = ChiefVerdictModel(**data)
        result = model.model_dump()
        return merge_chief_verdict(result, computed)
    except ValidationError:
        return merge_chief_verdict(data, computed)


def merge_chief_verdict(parsed: dict[str, Any], computed: dict[str, Any]) -> dict[str, Any]:
    """Keep Python-computed scores; fill narrative fields from Chief LLM."""
    agent_scores = computed.get("agent_scores", {})
    merged: dict[str, Any] = {
        "overall_score": computed.get("overall_score", 50),
        "risk_level": computed.get("risk_level", "MEDIUM"),
        "verdict": computed.get("verdict", "IMPROVE"),
        "agent_scores": agent_scores,
        "executive_summary": parsed.get("executive_summary")
        or _fallback_summary(computed),
        "top_strengths": parsed.get("top_strengths") or [],
        "top_weaknesses": parsed.get("top_weaknesses") or [],
        "contradictions": parsed.get("contradictions") or computed.get("contradictions") or [],
        "blocking_issues": parsed.get("blocking_issues") or computed.get("blocking_issues") or [],
        "recommended_fixes": _normalize_string_list(parsed.get("recommended_fixes")),
        "roadmap": _normalize_string_list(parsed.get("roadmap") or parsed.get("deployment_roadmap")),
        "deployment_roadmap": _normalize_string_list(parsed.get("deployment_roadmap") or parsed.get("roadmap")),
        "detected_technologies": _normalize_string_list(computed.get("detected_technologies") or parsed.get("detected_technologies")),
        "detected_algorithms": _normalize_string_list(computed.get("detected_algorithms") or parsed.get("detected_algorithms")),
        "architecture_summary": computed.get("architecture_summary") or parsed.get("architecture_summary", ""),
        "evidence_found": _normalize_string_list(computed.get("evidence_found") or parsed.get("evidence_found")),
        "evidence_missing": _normalize_string_list(computed.get("evidence_missing") or parsed.get("evidence_missing")),
        "calibration_explanation": computed.get("calibration_explanation") or parsed.get("calibration_explanation", ""),
        "project_type_justification": computed.get("project_type_justification") or parsed.get("project_type_justification", ""),
        "community_impact_score": computed.get("community_impact_score", parsed.get("community_impact_score", 0)),
    }

    if not merged["recommended_fixes"]:
        merged["recommended_fixes"] = _default_fixes(agent_scores)
    if not merged["roadmap"]:
        merged["roadmap"] = _default_roadmap(merged["verdict"])
    if not merged["deployment_roadmap"]:
        merged["deployment_roadmap"] = list(merged["roadmap"])

    return merged


def _normalize_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        if len(value) > 3 and all(isinstance(item, str) and len(item) <= 1 for item in value):
            return _normalize_string_list("".join(value))
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.extend(_normalize_string_list(item))
            elif isinstance(item, dict):
                out.extend(_normalize_string_list(str(item.get("fix") or item.get("step") or item.get("action") or item)))
        return [item for item in dict.fromkeys(out) if len(item) > 1][:8]
    text = re.sub(r"(?i)\s+(?=phase\s+\d+[:.\-])", "\n", str(value).strip())
    text = re.sub(r"\s+(?=\d+[.)]\s+[A-Z])", "\n", text)
    return [
        re.sub(r"^\s*(?:[-*+]|->|=>|[0-9]+[.)]|[A-Za-z][.)])\s*", "", line).strip(" -\t")
        for line in re.split(r"\r?\n|;", text)
        if line.strip(" -\t")
    ][:8]


def _fallback_summary(computed: dict[str, Any]) -> str:
    score = computed.get("overall_score", 50)
    verdict = computed.get("verdict", "IMPROVE")
    return (
        f"YOWON AI multi-agent jury completed evaluation with an overall score of "
        f"{score}/100. Deployment recommendation: {verdict}."
    )


def _default_fixes(scores: dict[str, int]) -> list[str]:
    fixes: list[str] = []
    if scores.get("security", 100) < 70:
        fixes.append("Remediate security findings and rotate any exposed secrets")
    if scores.get("technical", 100) < 70:
        fixes.append("Improve test coverage and document architecture decisions")
    if scores.get("presentation", 100) < 70:
        fixes.append("Strengthen pitch deck with problem, solution, and demo narrative")
    if not fixes:
        fixes.append("Add health checks and monitoring before production deploy")
    return fixes[:5]


def _default_roadmap(verdict: str) -> list[str]:
    if verdict == "ACCEPT":
        return [
            "Run staging deployment with synthetic load tests",
            "Harden security review and secrets management",
            "Configure canary release to limited production traffic",
            "Prepare full rollout with observability dashboards",
        ]
    if verdict == "REJECT":
        return [
            "Address blocking security and stability issues",
            "Re-run YOWON AI evaluation after fixes",
            "Pilot deploy only after score exceeds 50",
        ]
    return [
        "Fix top blocking issues identified by the jury",
        "Run staging deployment with integration tests",
        "Re-evaluate and proceed to canary release",
    ]
