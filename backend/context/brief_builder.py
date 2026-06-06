"""Deterministic evaluation brief — replaces coordination LLM call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationBrief:
    summary: str
    available_inputs: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    security_risk: str = "UNKNOWN"

    def to_text(self) -> str:
        lines = [
            f"PROJECT SUMMARY: {self.summary}",
            f"AVAILABLE INPUTS: {', '.join(self.available_inputs) or 'none'}",
            f"MISSING INFORMATION: {', '.join(self.missing) or 'none'}",
            f"RED FLAGS: {', '.join(self.red_flags) or 'none'}",
            f"STATIC SECURITY RISK: {self.security_risk}",
        ]
        return "\n".join(lines)


def build_brief(ctx: dict[str, Any]) -> EvaluationBrief:
    available: list[str] = []
    missing: list[str] = []
    red_flags: list[str] = []

    gh = ctx.get("github") or {}
    if gh and not gh.get("error"):
        available.append("source code / repository")
    elif ctx.get("github_url") or gh:
        missing.append("valid repository data")
    else:
        missing.append("source code")

    pdf = ctx.get("pdf") or {}
    ppt = ctx.get("ppt") or {}
    if (pdf and not pdf.get("error")) or (ppt and not ppt.get("error")):
        available.append("presentation / documentation")
    else:
        missing.append("pitch deck or PDF")

    if ctx.get("description"):
        available.append("project description")

    sec = ctx.get("security") or {}
    risk = sec.get("risk_level", "UNKNOWN")
    if risk in ("HIGH", "CRITICAL"):
        red_flags.append(f"Static security scan: {risk}")
    secret_count = len(sec.get("secret_findings", []))
    if secret_count:
        red_flags.append(f"{secret_count} potential secret(s) detected")

    bandit_count = len(sec.get("bandit_issues", []))
    if bandit_count >= 3:
        red_flags.append(f"{bandit_count} Bandit SAST findings")

    summary = ctx.get("project_name", "Unknown project")
    desc = (ctx.get("description") or "").strip()
    if desc:
        summary = f"{summary} — {desc[:180]}"

    return EvaluationBrief(
        summary=summary,
        available_inputs=available,
        missing=missing,
        red_flags=red_flags,
        security_risk=risk,
    )
