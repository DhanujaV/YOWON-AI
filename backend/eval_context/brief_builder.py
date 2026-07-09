"""Deterministic evaluation brief — no LLM required."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from scoring.rubrics import rubric_prompt

if TYPE_CHECKING:
    from eval_context.evaluation_context import EvaluationSession


@dataclass
class EvaluationBrief:
    summary:             str
    project_type:        str           = "Hackathon Project"
    available_inputs:    list[str]     = field(default_factory=list)
    missing:             list[str]     = field(default_factory=list)
    red_flags:           list[str]     = field(default_factory=list)
    repository_metrics:  dict[str, int]= field(default_factory=dict)
    evidence_summary:    list[str]     = field(default_factory=list)
    security_risk:       str           = "UNKNOWN"

    def to_text(self) -> str:
        lines = [
            rubric_prompt(self.project_type),
            f"PROJECT SUMMARY: {self.summary}",
            f"AVAILABLE INPUTS: {', '.join(self.available_inputs) or 'none'}",
            f"MISSING INFORMATION: {', '.join(self.missing) or 'none'}",
            f"STATIC SECURITY RISK: {self.security_risk}",
        ]
        if self.repository_metrics:
            metric_text = ", ".join(
                f"{key}={value}" for key, value in self.repository_metrics.items()
                if key in {
                    "total_files", "code_files", "documentation_files", "test_files",
                    "configuration_files", "deployment_files", "data_files", "meaningful_files",
                }
            )
            lines.append(f"REPOSITORY METRICS: {metric_text}")
        if self.evidence_summary:
            lines.append("SHARED EVIDENCE SUMMARY: " + "; ".join(self.evidence_summary))
        if self.red_flags:
            lines.append("RED FLAGS: " + "; ".join(self.red_flags))
        return "\n".join(lines)


def build_brief(
    ctx: dict[str, Any],
    session: Optional["EvaluationSession"] = None,
) -> EvaluationBrief:
    """
    Build a deterministic evaluation brief shared by all agents.

    When an EvaluationSession is available, Repository Intelligence enriches
    the brief with health scores, evidence counts, and recommendations.
    Legacy ctx keys are used for availability tracking and document detection.
    """
    available: list[str] = []
    missing:   list[str] = []
    red_flags: list[str] = []

    gh      = ctx.get("github") or {}
    metrics = gh.get("repository_statistics") or {}

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

    evidence_summary: list[str] = []

    # ── Incorporate Repository Intelligence when session is available ──────
    if session is not None:
        intel = session.repository_intelligence
        available.append("repository intelligence (static analysis)")

        health = intel.health_metrics
        if health:
            overall = health.get("overall", health.get("overall_score", 0))
            if overall:
                evidence_summary.append(f"codebase health: {overall}/100")
            if health.get("testing", 0) > 0:
                evidence_summary.append(f"test coverage health: {health['testing']}/100")
            if health.get("documentation", 0) > 0:
                evidence_summary.append(f"documentation health: {health['documentation']}/100")

        if intel.evidence:
            evidence_summary.append(f"{len(intel.evidence)} static analysis evidence records")
            categories = list({
                ev.get("category") or ev.get("rule_id", "").split("_")[1] if "_" in ev.get("rule_id", "") else ""
                for ev in intel.evidence[:20] if ev
            } - {""})
            if categories:
                evidence_summary.append(f"evidence categories: {', '.join(categories[:5])}")

        if intel.recommendations:
            evidence_summary.append(f"{len(intel.recommendations)} automated recommendations")

        if intel.detected_technologies:
            evidence_summary.append(f"technologies: {', '.join(intel.detected_technologies[:6])}")

        if intel.architecture:
            layer_count = (
                len(intel.architecture.get("nodes", [])) if "nodes" in intel.architecture
                else len(intel.architecture)
            )
            if layer_count:
                evidence_summary.append(f"{layer_count} architecture component(s) detected")

        # Security from RI (security_findings: None = not run, [] = clean)
        if intel.security_findings is None:
            red_flags.append("Security scan result unavailable")
        elif intel.security_findings:
            critical_high = [
                f for f in intel.security_findings
                if f.get("severity") in ("CRITICAL", "HIGH")
            ]
            if critical_high:
                red_flags.append(f"{len(critical_high)} CRITICAL/HIGH security finding(s)")
            evidence_summary.append(f"{len(intel.security_findings)} security finding(s) from static analysis")
        else:
            evidence_summary.append("security scan: CLEAN")

        # Intelligence quality score
        iq = getattr(intel, "intelligence_quality", None) or getattr(intel, "quality", None)
        if iq and isinstance(iq, dict):
            overall_iq = iq.get("overall_score", iq.get("score", 0))
            if overall_iq:
                evidence_summary.append(
                    f"RI quality score: {int(overall_iq * 100)}%"
                    if overall_iq <= 1.0
                    else f"RI quality score: {int(overall_iq)}/100"
                )

    else:
        # ── Legacy path: non-repository evaluations ───────────────────────
        code = ctx.get("code_reader") or {}
        tech_evidence = ctx.get("technical_evidence") or {}
        architecture = ctx.get("architecture") or {}

        if metrics:
            if metrics.get("documentation_files", 0) > 0:
                evidence_summary.append("documentation present")
            if metrics.get("test_files", 0) > 0:
                evidence_summary.append("tests present")
            if metrics.get("deployment_files", 0) > 0:
                evidence_summary.append("deployment files present")
            if metrics.get("source_modules", 0) >= 2:
                evidence_summary.append("modular source structure")
        if code.get("frameworks"):
            evidence_summary.append("frameworks detected: " + ", ".join(code["frameworks"][:4]))
        if tech_evidence.get("evidence_found"):
            evidence_summary.append("implementation evidence: " + ", ".join(tech_evidence["evidence_found"][:6]))
        if architecture.get("summary"):
            evidence_summary.append(architecture["summary"])

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

    # Security risk level for brief header
    security_risk = "UNKNOWN"
    if session and session.repository_intelligence.security_findings:
        sevs = [f.get("severity", "LOW") for f in session.repository_intelligence.security_findings]
        if "CRITICAL" in sevs:
            security_risk = "CRITICAL"
        elif "HIGH" in sevs:
            security_risk = "HIGH"
        elif "MEDIUM" in sevs:
            security_risk = "MEDIUM"
        else:
            security_risk = "LOW"
    elif session and session.repository_intelligence.security_findings is not None:
        security_risk = "LOW"
    else:
        sec = ctx.get("security") or {}
        security_risk = sec.get("risk_level", "UNKNOWN")

    return EvaluationBrief(
        summary          = summary,
        project_type     = ctx.get("project_type", "Hackathon Project"),
        available_inputs = available,
        missing          = missing,
        red_flags        = red_flags,
        repository_metrics = metrics,
        evidence_summary = evidence_summary,
        security_risk    = security_risk,
    )
