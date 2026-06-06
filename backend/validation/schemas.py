"""Pydantic schemas for structured agent outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    deployment_roadmap: list[str] = Field(default_factory=list)
    agent_scores: AgentScores
    project_type: str = "Hackathon Project"
    evaluation_standard: str = ""
    scoring_weights: dict[str, float] = Field(default_factory=dict)
    score_band: str = ""
    confidence: int = Field(ge=0, le=100, default=0)
    raw_weighted_score: int = 0
    penalties: list[dict] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)

    @field_validator("recommended_fixes", "deployment_roadmap", mode="before")
    @classmethod
    def coerce_fixes(cls, v):
        if not v:
            return []
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                fix = item.get("fix") or item.get("step") or str(item)
                effort = item.get("effort")
                priority = item.get("priority")
                if effort or priority:
                    out.append(f"[P{priority or '?'}] {fix} (effort: {effort or 'TBD'})")
                else:
                    out.append(str(fix))
        return out
