"""Pydantic schemas for structured agent outputs."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


DEFAULT_ROADMAP = [
    "Stabilize evidence package with README, architecture notes, and setup instructions",
    "Add automated tests and publish repeatable validation results",
    "Harden security, dependency, and secrets-management controls",
    "Prepare deployment assets, observability, and rollback steps",
    "Re-run YOWON AI evaluation before production or demo release",
]


def _normalize_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        text = re.sub(r"(?i)\s+(?=phase\s+\d+[:.\-])", "\n", value.strip())
        text = re.sub(r"\s+(?=\d+[.)]\s+[A-Z])", "\n", text)
        return [
            re.sub(r"^\s*(?:[-*+]|->|=>|[0-9]+[.)]|[A-Za-z][.)])\s*", "", line).strip(" -\t")
            for line in re.split(r"\r?\n|;", text)
            if line.strip(" -\t")
        ]
    if isinstance(value, list):
        if len(value) > 3 and all(isinstance(item, str) and len(item) <= 1 for item in value):
            return _normalize_string_list("".join(value))
        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                fix = item.get("fix") or item.get("step") or item.get("action") or item.get("factor") or str(item)
                effort = item.get("effort")
                priority = item.get("priority")
                text = f"[P{priority or '?'}] {fix} (effort: {effort or 'TBD'})" if effort or priority else str(fix)
                out.extend(_normalize_string_list(text))
            else:
                out.extend(_normalize_string_list(str(item)))
        return [item for item in dict.fromkeys(out) if len(item) > 1]
    return _normalize_string_list(str(value))


class TechnicalReport(BaseModel):
    technical_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list, max_length=3)
    weaknesses: list[str] = Field(default_factory=list, max_length=3)
    risks: list[str] = Field(default_factory=list, max_length=3)
    confidence: float = Field(ge=0, le=1, default=0.5)


class SecurityReport(BaseModel):
    security_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    critical_findings: list[str] = Field(default_factory=list, max_length=5)
    confidence: float = Field(ge=0, le=1, default=0.5)


class InnovationReport(BaseModel):
    innovation_score: int = Field(ge=0, le=100)
    scalability_score: int = Field(ge=0, le=100)
    differentiators: list[str] = Field(default_factory=list, max_length=3)
    scalability_risk: str = ""
    confidence: float = Field(ge=0, le=1, default=0.5)


class PresentationReport(BaseModel):
    presentation_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvements: list[str] = Field(default_factory=list, max_length=3)
    confidence: float = Field(ge=0, le=1, default=0.5)
    status: str = "OK"


class RiskReport(BaseModel):
    impact_score: int = Field(ge=0, le=100)
    failure_modes: list[str] = Field(default_factory=list, max_length=5)
    top_risks: list[str] = Field(default_factory=list, max_length=5)
    confidence: float = Field(ge=0, le=1, default=0.5)


class AgentScores(BaseModel):
    technical: int
    security: int
    scalability: int
    innovation: int
    presentation: int
    impact: int


class ChiefVerdict(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    verdict: Literal["ACCEPT","CONDITIONAL_APPROVE", "IMPROVE", "REJECT"]
    executive_summary: str = ""
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    recommended_fixes: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)
    deployment_roadmap: list[str] = Field(default_factory=list)
    agent_scores: AgentScores
    raw_agent_scores: AgentScores
    calibrated_agent_scores: AgentScores
    agent_calibration_reasons: dict[str, list[str]] = Field(default_factory=dict)
    project_type: str = "Hackathon Project"
    submitted_project_type: str = ""
    detected_project_type: str = ""
    detected_project_confidence: float = 0
    evaluation_standard: str = ""
    scoring_weights: dict[str, float] = Field(default_factory=dict)
    score_band: str = ""
    confidence: int = Field(ge=0, le=100, default=0)
    confidence_explanation: str = ""
    confidence_sources: list[str] = Field(default_factory=list)
    repository_statistics: dict[str, int] = Field(default_factory=dict)
    repository_completeness_score: int = Field(ge=0, le=100, default=0)
    evidence_quality: str = ""
    raw_weighted_score: int = 0
    penalties: list[dict] = Field(default_factory=list)
    calibration_adjustments: list[dict] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    detected_technologies: list[str] = Field(default_factory=list)
    detected_algorithms: list[str] = Field(default_factory=list)
    architecture_summary: str = ""
    evidence_found: list[str] = Field(default_factory=list)
    evidence_missing: list[str] = Field(default_factory=list)
    confidence_explanation: str = ""
    calibration_explanation: str = ""
    project_type_justification: str = ""
    community_impact_score: int = Field(ge=0, le=100, default=0)

    @field_validator("recommended_fixes", "roadmap", "deployment_roadmap", "confidence_sources", mode="before")
    @classmethod
    def coerce_fixes(cls, v):
        return _normalize_string_list(v)

    @model_validator(mode="after")
    def sync_roadmap_aliases(self):
        if self.roadmap and not self.deployment_roadmap:
            self.deployment_roadmap = list(self.roadmap)
        if self.deployment_roadmap and not self.roadmap:
            self.roadmap = list(self.deployment_roadmap)
        if not self.roadmap and not self.deployment_roadmap:
            self.roadmap = list(DEFAULT_ROADMAP)
            self.deployment_roadmap = list(DEFAULT_ROADMAP)
        if not self.positive_factors:
            self.positive_factors = ["Evidence profile generated"]
        if not self.missing_evidence:
            self.missing_evidence = ["No additional missing evidence detected"]
        return self
