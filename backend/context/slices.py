"""Per-agent context slices to reduce token usage."""

from __future__ import annotations

from typing import Any


def _gh(ctx: dict) -> dict:
    return ctx.get("github") or {}


def _sec(ctx: dict) -> dict:
    return ctx.get("security") or {}


def _format_security(sec: dict) -> str:
    if not sec:
        return "No static security analysis available."
    lines = [
        f"Risk Level: {sec.get('risk_level', 'N/A')}",
        sec.get("summary", ""),
    ]
    for issue in sec.get("secret_findings", [])[:8]:
        lines.append(f"- SECRET: {issue.get('issue')} at {issue.get('file')}:{issue.get('line')}")
    for issue in sec.get("bandit_issues", [])[:8]:
        lines.append(f"- BANDIT [{issue.get('severity')}]: {issue.get('issue')}")
    for w in sec.get("dependency_warnings", [])[:5]:
        lines.append(f"- DEP: {w.get('issue')}")
    return "\n".join(lines)


def slice_context_for_agents(ctx: dict[str, Any]) -> dict[str, str]:
    gh = _gh(ctx)
    sec = _sec(ctx)
    pdf = ctx.get("pdf") or {}
    ppt = ctx.get("ppt") or {}

    technical_parts = [
        f"Project: {ctx.get('project_name', '')}",
        f"Description: {(ctx.get('description') or '')[:800]}",
    ]
    if gh and not gh.get("error"):
        technical_parts.extend([
            f"Repo: {gh.get('name')} | Language: {gh.get('language')}",
            f"README excerpt:\n{(gh.get('readme') or '')[:2000]}",
            "Folder structure:\n" + "\n".join((gh.get("folder_structure") or [])[:40]),
        ])
        deps = gh.get("dependencies") or {}
        if deps:
            technical_parts.append(
                "Dependencies:\n" + "\n".join(f"{k}: {v[:300]}" for k, v in list(deps.items())[:6])
            )

    security_parts = [
        f"Project: {ctx.get('project_name', '')}",
        _format_security(sec),
    ]
    if gh.get("dependencies"):
        security_parts.append(
            "Dependency files:\n"
            + "\n".join(f"{k}: {v[:400]}" for k, v in list(gh["dependencies"].items())[:4])
        )

    innovation_parts = [
        f"Project: {ctx.get('project_name', '')}",
        f"Description: {(ctx.get('description') or '')[:1200]}",
    ]
    if gh and not gh.get("error"):
        innovation_parts.append(f"Topics: {', '.join(gh.get('topics') or [])}")
        innovation_parts.append(f"README excerpt:\n{(gh.get('readme') or '')[:1200]}")

    presentation_parts = [
        f"Project: {ctx.get('project_name', '')}",
        f"Description: {(ctx.get('description') or '')[:600]}",
    ]
    if ppt and not ppt.get("error"):
        presentation_parts.append(f"Slides ({ppt.get('slide_count', 0)}):\n{(ppt.get('full_text') or '')[:3500]}")
    if pdf and not pdf.get("error"):
        presentation_parts.append(f"PDF ({pdf.get('page_count', 0)} pages):\n{(pdf.get('full_text') or '')[:3500]}")
    if not ppt and not pdf:
        presentation_parts.append("No presentation file uploaded.")

    risk_parts = [
        f"Project: {ctx.get('project_name', '')}",
        f"Description: {(ctx.get('description') or '')[:1000]}",
        _format_security(sec),
    ]

    return {
        "technical": "\n\n".join(technical_parts)[:3500],
        "security": "\n\n".join(security_parts)[:3500],
        "innovation": "\n\n".join(innovation_parts)[:3000],
        "presentation": "\n\n".join(presentation_parts)[:3500],
        "risk": "\n\n".join(risk_parts)[:3000],
    }
