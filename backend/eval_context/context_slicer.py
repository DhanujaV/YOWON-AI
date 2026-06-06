"""Slice project context into compact agent-specific digests."""

from __future__ import annotations

from typing import Any

from config import MAX_AGENT_DIGEST_CHARS, MAX_BRIEF_CHARS


def truncate_text(text: str, limit: int, *, label: str = "text") -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 24] + f"\n...[truncated {label}]"


def _gh_excerpt(ctx: dict[str, Any], readme_limit: int = 900) -> str:
    gh = ctx.get("github") or {}
    if not gh or gh.get("error"):
        return "[No repository data]"
    parts = [
        f"Repo: {gh.get('name', 'unknown')}",
        f"Language: {gh.get('language', 'unknown')}",
        f"Stars: {gh.get('stars', 0)}",
    ]
    if gh.get("readme"):
        parts.append(f"README excerpt:\n{gh['readme'][:readme_limit]}")
    deps = gh.get("dependencies") or {}
    if deps:
        dep_text = "\n".join(f"{k}: {v[:200]}" for k, v in list(deps.items())[:4])
        parts.append(f"Dependencies:\n{dep_text}")
    structure = gh.get("folder_structure") or []
    if structure:
        parts.append("Structure:\n" + "\n".join(structure[:25]))
    return "\n".join(parts)


def _security_digest(ctx: dict[str, Any]) -> str:
    sec = ctx.get("security") or {}
    if not sec:
        return "[No static security scan]"
    lines = [
        f"Risk Level: {sec.get('risk_level', 'N/A')}",
        (sec.get("summary") or "")[:400],
    ]
    for issue in sec.get("secret_findings", [])[:6]:
        lines.append(f"- {issue.get('issue')} @ {issue.get('file')}:{issue.get('line')}")
    for issue in sec.get("bandit_issues", [])[:5]:
        lines.append(f"- Bandit: {issue.get('issue')} ({issue.get('severity')})")
    for w in sec.get("dependency_warnings", [])[:4]:
        lines.append(f"- Dep: {w.get('issue')}")
    return "\n".join(lines)


def _doc_digest(ctx: dict[str, Any]) -> str:
    parts: list[str] = []
    pdf = ctx.get("pdf") or {}
    if pdf and not pdf.get("error"):
        parts.append(
            f"PDF ({pdf.get('page_count', 0)} pages):\n"
            f"{(pdf.get('full_text') or '')[:1200]}"
        )
    ppt = ctx.get("ppt") or {}
    if ppt and not ppt.get("error"):
        parts.append(
            f"PPT ({ppt.get('slide_count', 0)} slides):\n"
            f"{(ppt.get('full_text') or '')[:1200]}"
        )
    if ctx.get("description"):
        parts.append(f"Description:\n{ctx['description'][:500]}")
    return "\n\n".join(parts) if parts else "[No presentation materials]"


def slice_context_for_agent(ctx: dict[str, Any], agent: str) -> str:
    brief_parts: list[str] = [
        f"Project: {ctx.get('project_name', 'Unknown')}",
        f"PROJECT_TYPE: {ctx.get('project_type', 'Hackathon Project')}",
    ]

    if agent == "technical":
        brief_parts.append(_gh_excerpt(ctx, readme_limit=1000))
    elif agent == "security":
        brief_parts.append(_security_digest(ctx))
        gh = ctx.get("github") or {}
        deps = gh.get("dependencies") or {}
        if deps:
            brief_parts.append(
                "Dependency files:\n"
                + "\n".join(f"{k}:\n{v[:250]}" for k, v in list(deps.items())[:3])
            )
    elif agent == "presentation":
        brief_parts.append(_doc_digest(ctx))
    elif agent == "innovation":
        brief_parts.append((ctx.get("description") or "")[:400])
        gh = ctx.get("github") or {}
        if gh and not gh.get("error"):
            topics = ", ".join(gh.get("topics", [])[:8])
            brief_parts.append(f"Topics: {topics}")
            brief_parts.append(_gh_excerpt(ctx, readme_limit=700))
    elif agent == "risk":
        brief_parts.append((ctx.get("description") or "")[:350])
        brief_parts.append(_security_digest(ctx)[:500])
        brief_parts.append(_gh_excerpt(ctx, readme_limit=500))
    else:
        brief_parts.append(_gh_excerpt(ctx, readme_limit=600))
        brief_parts.append(_doc_digest(ctx))

    text = "\n\n".join(brief_parts)
    return truncate_text(text, MAX_AGENT_DIGEST_CHARS, label=f"digest:{agent}")


def truncate_brief(brief_text: str) -> str:
    return truncate_text(brief_text, MAX_BRIEF_CHARS, label="brief")
