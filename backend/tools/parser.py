"""
tools/parser.py â€” Central data bundler for YOWON AI.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional

from logging_config import get_logger
from tools.github_tool import extract_github_data
from tools.pdf_tool import extract_pdf_data
from tools.ppt_tool import extract_ppt_data
from tools.security_tool import run_security_analysis
from analysis.code_intelligence import (
    detect_project_type,
    extract_technical_evidence,
    read_codebase,
    summarize_architecture,
)

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
        "submitted_project_type": project_type,
        "detected_project_type": "",
        "detected_project_confidence": 0,
        "description": description,
        "github": {},
        "pdf": {},
        "ppt": {},
        "security": {},
        "code_reader": {},
        "architecture": {},
        "project_type_detection": {},
        "technical_evidence": {},
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures: dict[str, Any] = {}
        if github_url:
            if on_phase:
                on_phase("Fetching repository")
            futures["github"] = executor.submit(extract_github_data, github_url)
        if pdf_path and Path(pdf_path).exists():
            futures["pdf"] = executor.submit(extract_pdf_data, pdf_path)
        if ppt_path and Path(ppt_path).exists():
            futures["ppt"] = executor.submit(extract_ppt_data, ppt_path)

        for key, future in futures.items():
            t0 = time.perf_counter()
            ctx[key] = future.result()
            logger.info("%s parse/fetch duration=%.2fs", key.upper(), time.perf_counter() - t0)

    if ctx.get("github") and not ctx["github"].get("error"):
        python_files = ctx["github"].get("python_files", [])
        source_files = ctx["github"].get("source_files", [])
        dep_files = ctx["github"].get("dependencies", {})
        with ThreadPoolExecutor(max_workers=2) as executor:
            security_future = None
            if python_files or source_files or dep_files:
                security_future = executor.submit(run_security_analysis, python_files, dep_files, source_files)

            t0 = time.perf_counter()
            ctx["code_reader"] = read_codebase(ctx)
            ctx["architecture"] = summarize_architecture(ctx, ctx["code_reader"])
            ctx["technical_evidence"] = extract_technical_evidence(ctx, ctx["code_reader"], ctx["architecture"])
            ctx["project_type_detection"] = detect_project_type(ctx, ctx["code_reader"], ctx["architecture"])
            logger.info("Code intelligence duration=%.2fs", time.perf_counter() - t0)

            if security_future:
                t0 = time.perf_counter()
                ctx["security"] = security_future.result()
                logger.info("Security scan duration=%.2fs", time.perf_counter() - t0)

        detection = ctx["project_type_detection"]
        ctx["detected_project_type"] = detection.get("project_type", "")
        ctx["detected_project_confidence"] = detection.get("confidence", 0)
        if project_type == "Auto Detect" and detection.get("project_type"):
            ctx["project_type"] = detection["project_type"]
        logger.info(
            "Project type detected=%s confidence=%s submitted=%s effective=%s",
            detection.get("project_type"),
            detection.get("confidence"),
            project_type,
            ctx["project_type"],
        )

    return ctx


def context_to_text(ctx: dict[str, Any]) -> str:
    """Flatten context for Chroma â€” compact summaries only."""
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

    code = ctx.get("code_reader") or {}
    if code:
        parts.append("\n## Code Reader Summary")
        parts.append(code.get("summary", ""))
        if code.get("frameworks"):
            parts.append("Frameworks: " + ", ".join(code["frameworks"]))
        if code.get("algorithms"):
            parts.append("Algorithms: " + ", ".join(code["algorithms"]))

    arch = ctx.get("architecture") or {}
    if arch:
        parts.append("\n## Architecture Summary")
        parts.append(arch.get("summary", ""))

    evidence = ctx.get("technical_evidence") or {}
    if evidence:
        parts.append("\n## Implementation Evidence")
        parts.append("Evidence Found: " + ", ".join(evidence.get("evidence_found", [])))
        parts.append("Evidence Missing: " + ", ".join(evidence.get("evidence_missing", [])))
        for label, key in (
            ("REST APIs Found", "rest_apis_found"),
            ("Database Usage", "database_usage"),
            ("Authentication Usage", "authentication_usage"),
            ("Integrations", "integrations"),
        ):
            values = evidence.get(key) or []
            if values:
                parts.append(f"{label}: " + " | ".join(str(item) for item in values[:6]))
        snippets = evidence.get("top_code_snippets") or []
        if snippets:
            parts.append(
                "\n### Top Code Snippets\n"
                + "\n\n".join(
                    f"{item.get('path')}:\n{str(item.get('snippet') or '')[:900]}"
                    for item in snippets[:4]
                )
            )

    detection = ctx.get("project_type_detection") or {}
    if detection:
        parts.append(
            f"\n## Project Type Detection\nDetected: {detection.get('project_type')} "
            f"(confidence {detection.get('confidence')})\n{detection.get('justification', '')}"
        )

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
