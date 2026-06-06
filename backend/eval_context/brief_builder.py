"""Deterministic evaluation brief — no LLM required."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from scoring.rubrics import rubric_prompt


@dataclass
class EvaluationBrief:
    summary: str
    project_type: str = "Hackathon Project"
    available_inputs: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    security_risk: str = "UNKNOWN"

    def to_text(self) -> str:
        lines = [
            rubric_prompt(self.project_type),
            f"PROJECT SUMMARY: {self.summary}",
            f"AVAILABLE INPUTS: {', '.join(self.available_inputs) or 'none'}",
            f"MISSING INFORMATION: {', '.join(self.missing) or 'none'}",
            f"STATIC SECURITY RISK: {self.security_risk}",
        ]
        if self.red_flags:
            lines.append("RED FLAGS: " + "; ".join(self.red_flags))
        return "\n".join(lines)


def build_brief(ctx: dict[str, Any]) -> EvaluationBrief:
    available: list[str] = []
    missing: list[str] = []
    red_flags: list[str] = []

    gh = ctx.get("github") or {}
    if gh and not gh.get("error"):
        available.append("source code")
    else:
        missing.append("source code")

    if ctx.get("pdf") and not ctx["pdf"].get("error"):
        available.append("PDF documentation")
    if ctx.get("ppt") and not ctx["ppt"].get("error"):
        available.append("presentation deck")
    if not any(x in available for x in ("PDF documentation", "presentation deck")):
        missing.append("pitch deck or PDF")

    if ctx.get("description"):
        available.append("project description")

    sec = ctx.get("security") or {}
    risk = sec.get("risk_level", "UNKNOWN")
    if risk in ("HIGH", "CRITICAL"):
        red_flags.append(f"Static security scan: {risk}")
    secret_count = len(sec.get("secret_findings", []))
    if secret_count:
        red_flags.append(f"{secret_count} potential secret(s) in code")

    summary = f"{ctx.get('project_name', 'Unknown')}"
    desc = (ctx.get("description") or "").strip()
    if desc:
        summary += f" — {desc[:180]}"

    return EvaluationBrief(
        summary=summary,
        project_type=ctx.get("project_type", "Hackathon Project"),
        available_inputs=available,
        missing=missing,
        red_flags=red_flags,
        security_risk=risk,
    )
