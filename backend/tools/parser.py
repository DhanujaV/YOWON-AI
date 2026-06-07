"""
tools/parser.py — Central data bundler for Project Sentinel.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Optional

from logging_config import get_logger
from tools.github_tool import extract_github_data
from tools.pdf_tool import extract_pdf_data
from tools.ppt_tool import extract_ppt_data
from tools.security_tool import run_security_analysis

logger = get_logger(__name__)


def build_project_context(
    *,
    project_name: str,
    project_type: str = "Hackathon Project",
    description: str = "",
    github_url: Optional[str] = None,
    pdf_path: Optional[str] = None,
    ppt_path: Optional[str] = None,
    on_phase: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Aggregate all available project data into a single context dictionary.
    """
    ctx: dict[str, Any] = {
        "project_name": project_name,
        "project_type": project_type,
        "description": description,
        "github": {},
        "pdf": {},
        "ppt": {},
        "security": {},
    }

    if github_url:
        if on_phase:
            on_phase("Fetching repository")
        t0 = time.perf_counter()
        ctx["github"] = extract_github_data(github_url)
        logger.info(
            "GitHub fetch duration=%.2fs url=%s",
            time.perf_counter() - t0,
            github_url,
        )

    if pdf_path and Path(pdf_path).exists():
        t0 = time.perf_counter()
        ctx["pdf"] = extract_pdf_data(pdf_path)
        logger.info("PDF parse duration=%.2fs path=%s", time.perf_counter() - t0, pdf_path)

    if ppt_path and Path(ppt_path).exists():
        t0 = time.perf_counter()
        ctx["ppt"] = extract_ppt_data(ppt_path)
        logger.info("PPT parse duration=%.2fs path=%s", time.perf_counter() - t0, ppt_path)

    python_files = ctx["github"].get("python_files", [])
    dep_files = ctx["github"].get("dependencies", {})
    if python_files or dep_files:
        t0 = time.perf_counter()
        ctx["security"] = run_security_analysis(python_files, dep_files)
        logger.info("Security scan duration=%.2fs", time.perf_counter() - t0)

    return ctx


def context_to_text(ctx: dict[str, Any]) -> str:
    """Flatten context for Chroma — compact summaries only."""
    parts: list[str] = []

    parts.append(f"# Project: {ctx.get('project_name', 'Unknown')}")
    parts.append(f"Project Type: {ctx.get('project_type', 'Hackathon Project')}")
    if ctx.get("description"):
        parts.append(f"\n## Description\n{ctx['description'][:800]}")

    gh = ctx.get("github", {})
    if gh and not gh.get("error"):
        parts.append("\n## GitHub Repository")
        parts.append(f"- Repo: {gh.get('name')}")
        parts.append(f"- Language: {gh.get('language')}")
        parts.append(f"- Stars: {gh.get('stars')} | Forks: {gh.get('forks')}")
        parts.append(f"- Topics: {', '.join(gh.get('topics', []))}")
        stats = gh.get("repository_statistics") or {}
        if stats:
            parts.append(
                "\n### Repository Metrics\n"
                + "\n".join(
                    f"- {key.replace('_', ' ').title()}: {value}"
                    for key, value in stats.items()
                )
            )
        parts.append(f"\n### README (excerpt)\n{gh.get('readme', '')[:1500]}")
        deps = gh.get("dependencies", {})
        if deps:
            parts.append(
                "\n### Dependencies\n"
                + "\n".join(f"**{k}**:\n{v[:300]}" for k, v in list(deps.items())[:4])
            )
        structure = gh.get("folder_structure", [])
        if structure:
            parts.append("\n### Folder Structure\n" + "\n".join(structure[:30]))

    pdf = ctx.get("pdf", {})
    if pdf and not pdf.get("error"):
        parts.append(f"\n## PDF Document ({pdf.get('page_count', 0)} pages)")
        parts.append((pdf.get("full_text") or "")[:2000])

    ppt = ctx.get("ppt", {})
    if ppt and not ppt.get("error"):
        parts.append(f"\n## Presentation ({ppt.get('slide_count', 0)} slides)")
        parts.append((ppt.get("full_text") or "")[:2000])

    sec = ctx.get("security", {})
    if sec:
        parts.append("\n## Static Security Analysis")
        parts.append(f"Risk Level: {sec.get('risk_level', 'N/A')}")
        parts.append((sec.get("summary") or "")[:500])
        for issue in sec.get("secret_findings", [])[:8]:
            parts.append(f"  - {issue['issue']} at {issue['file']}:{issue['line']}")

    return "\n".join(parts)
