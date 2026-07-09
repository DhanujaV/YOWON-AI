"""
context_slicer.py — Build deterministic, agent-specific context digests.

Repository Intelligence (via EvaluationSession) is the SOLE source of code
knowledge injected into agent prompts. Legacy ctx keys (code_reader,
technical_evidence, architecture) are used only as non-code supplementary
material (project description, GitHub metadata, PDF/PPT).
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from config import MAX_AGENT_DIGEST_CHARS, MAX_BRIEF_CHARS

if TYPE_CHECKING:
    from eval_context.evaluation_context import EvaluationSession


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def truncate_text(text: str, limit: int, *, label: str = "text") -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 24] + f"\n...[truncated {label}]"


# ─────────────────────────────────────────────────────────────────────────────
# Non-code context helpers (GitHub metadata, PDF, PPT)
# These read from ctx, which still holds project-level info
# ─────────────────────────────────────────────────────────────────────────────

def _gh_excerpt(ctx: dict[str, Any], readme_limit: int = 900) -> str:
    gh = ctx.get("github") or {}
    if not gh or gh.get("error"):
        return "[No repository data]"
    parts = [
        f"Repo: {gh.get('name', 'unknown')}",
        f"Language: {gh.get('language', 'unknown')}",
        f"Stars: {gh.get('stars', 0)}",
    ]
    stats = gh.get("repository_statistics") or {}
    if stats:
        parts.append(
            "Repository metrics: "
            + ", ".join(
                f"{key}={value}" for key, value in stats.items()
                if key in {
                    "total_files", "code_files", "documentation_files", "test_files",
                    "configuration_files", "deployment_files", "data_files", "meaningful_files",
                }
            )
        )
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


def _doc_digest(ctx: dict[str, Any]) -> str:
    parts: list[str] = []
    if ctx.get("project_name"):
        parts.append(f"Project Name: {ctx['project_name']}")
    if ctx.get("description"):
        parts.append(f"Project Description & Presentation Links:\n{ctx['description']}")
    pdf = ctx.get("pdf") or {}
    if pdf and not pdf.get("error"):
        parts.append(
            f"PDF Documentation ({pdf.get('page_count', 0)} pages):\n"
            f"{(pdf.get('full_text') or '')[:3500]}"
        )
    ppt = ctx.get("ppt") or {}
    if ppt and not ppt.get("error"):
        parts.append(
            f"PPT Presentation/Pitch Deck ({ppt.get('slide_count', 0)} slides):\n"
            f"{(ppt.get('full_text') or '')[:3500]}"
        )
    gh = ctx.get("github") or {}
    if gh and not gh.get("error"):
        if gh.get("readme"):
            parts.append(f"GitHub README documentation:\n{gh['readme'][:2000]}")
        source_files = gh.get("source_files") or []
        images = [
            f["path"] for f in source_files
            if isinstance(f, dict) and f.get("path") and any(
                str(f["path"]).lower().endswith(ext)
                for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")
            )
        ]
        if images:
            parts.append(f"UI Screenshots and Design Assets found: {', '.join(images[:15])}")
    digest_text = "\n\n".join(parts)
    if len(digest_text.strip()) < 100:
        return "[No presentation materials]"
    return digest_text


# ─────────────────────────────────────────────────────────────────────────────
# Repository Intelligence digest helpers — read from EvaluationSession
# ─────────────────────────────────────────────────────────────────────────────

def _format_health(health: dict[str, Any]) -> str:
    if not health:
        return ""
    lines = [
        f"  Overall Health:       {health.get('overall', health.get('overall_score', 0))}/100",
        f"  Documentation Health: {health.get('documentation', 0)}/100",
        f"  Testing Health:       {health.get('testing', 0)}/100",
        f"  Security Health:      {health.get('security', 0)}/100",
        f"  Code Quality:         {health.get('code_quality', 0)}/100",
    ]
    if health.get("maintainability"):
        lines.append(f"  Maintainability:      {health['maintainability']}/100")
    return "\n".join(lines)


def _format_metrics(complexity_metrics: dict[str, Any]) -> str:
    """Format file-level metrics. complexity_metrics is dict[file_path → metrics_dict]."""
    if not complexity_metrics or not isinstance(complexity_metrics, dict):
        return ""
    try:
        total_loc = sum(
            m.get("loc", 0) if isinstance(m, dict) else 0
            for m in complexity_metrics.values()
        )
        total_files = len(complexity_metrics)
        mi_values = [
            m.get("maintainability_index", 0)
            for m in complexity_metrics.values()
            if isinstance(m, dict) and m.get("maintainability_index") is not None
        ]
        avg_mi = round(sum(mi_values) / len(mi_values), 1) if mi_values else 0
        return (
            f"  Total LOC:                    {total_loc}\n"
            f"  Files Analyzed:               {total_files}\n"
            f"  Avg Maintainability Index:    {avg_mi}/100"
        )
    except Exception:
        return ""


def _format_architecture(architecture: dict[str, Any]) -> str:
    """Format architecture layers dict."""
    if not architecture:
        return ""
    # architecture_graph dict: layer_name → {description, files, techs}
    # OR graph format: {nodes: [...], edges: [...]}
    if "nodes" in architecture:
        # Graph format — extract layer labels
        layers = [
            n.get("label") or n.get("id")
            for n in architecture.get("nodes", [])
            if n.get("type") == "layer"
        ]
        layers = [str(l) for l in layers if l]
        return f"  Architecture Layers: {', '.join(layers) or 'None detected'}"
    # Dict format (from ArchitectureEngine.analyze → layers dict)
    layer_summaries = []
    for layer_name, layer_info in list(architecture.items())[:8]:
        if isinstance(layer_info, dict):
            techs = ", ".join(layer_info.get("techs", [])[:4])
            layer_summaries.append(f"  [{layer_name}]: {layer_info.get('description', '')} (techs: {techs})")
        else:
            layer_summaries.append(f"  [{layer_name}]")
    return "\n".join(layer_summaries)


def _format_dependencies(dependency_graph: dict[str, Any]) -> str:
    if not dependency_graph:
        return ""
    if "nodes" in dependency_graph:
        nodes = dependency_graph.get("nodes", [])
        dep_names = [n.get("label") or n.get("id") for n in nodes[:10] if n.get("label") or n.get("id")]
        warnings = dependency_graph.get("warnings") or []
        lines = [f"  Dependencies detected: {', '.join(str(d) for d in dep_names)}"]
        if warnings:
            lines.append(f"  Outdated/vulnerable: {len(warnings)} warning(s)")
            for w in warnings[:4]:
                lines.append(f"    * {w.get('package', '?')} → {w.get('warning_type', '?')}: {w.get('message', '')[:80]}")
        return "\n".join(lines)
    # Plain dict format
    dep_list = [f"{k}={v}" for k, v in list(dependency_graph.items())[:8]]
    return "  Dependencies: " + ", ".join(dep_list)


def _format_evidence(evidence: list[dict], agent: str) -> str:
    """Format evidence records filtered by agent relevance."""
    if not evidence:
        return ""

    AGENT_RULE_AFFINITY: dict[str, tuple[str, ...]] = {
        "technical":    ("FASTAPI", "SQLALCHEMY", "TREE", "METRICS", "DOCKER", "GITHUB_ACTIONS", "CELERY"),
        "security":     ("SECRET", "UNSAFE", "VULNERABILITY", "JWT", "AUTH", "BANDIT"),
        "risk":         ("AUTH", "GATEWAY", "CELERY", "DEPENDENCY", "VULN"),
        "innovation":   ("OLLAMA", "LANGCHAIN", "VECTOR", "ML", "AI"),
        "presentation": ("README", "DOC", "OPENAPI"),
    }

    affinity = AGENT_RULE_AFFINITY.get(agent, ())
    relevant = []
    for ev in evidence:
        rule_id = str(ev.get("rule_id", ""))
        if not affinity or any(kw in rule_id.upper() for kw in affinity):
            relevant.append(ev)

    # Fall back to first N if nothing matched by affinity
    if not relevant and evidence:
        relevant = evidence[:5]

    lines = []
    for ev in relevant[:8]:
        rule_id = ev.get("rule_id", "")
        file_path = ev.get("file_path", "")
        confidence = int((ev.get("confidence", 0) or 0) * 100)
        severity = ev.get("severity", "")
        line_start = ev.get("line_start", "")
        lines.append(
            f"  [{rule_id}] {file_path}:{line_start} — confidence {confidence}%"
            + (f" [{severity}]" if severity else "")
        )
    return "\n".join(lines)


def _format_security_findings(security_findings: Optional[list]) -> str:
    """
    Format security findings for injection into Security/Risk agent prompts.
    None = scan not run. [] = clean. List = issues found.
    """
    if security_findings is None:
        return "  Security scan result: NOT AVAILABLE"
    if not security_findings:
        return "  Security scan result: CLEAN — no issues detected"
    lines = [f"  Security findings ({len(security_findings)} total):"]
    for finding in security_findings[:8]:
        severity = finding.get("severity", "?")
        rule_id = finding.get("rule_id", finding.get("issue", "?"))
        file_path = finding.get("file_path", finding.get("file", "?"))
        lines.append(f"    [{severity}] {rule_id} in {file_path}")
    return "\n".join(lines)


def _format_recommendations(recommendations: list[dict], agent: str) -> str:
    AGENT_CATEGORY_AFFINITY: dict[str, tuple[str, ...]] = {
        "technical":    ("IMPLEMENTATION", "ARCHITECTURE", "TESTING", "DEPLOYMENT"),
        "security":     ("SECURITY",),
        "risk":         ("RISK", "SECURITY"),
        "innovation":   ("ML", "SCALABILITY", "INNOVATION"),
    }
    cats = AGENT_CATEGORY_AFFINITY.get(agent)
    relevant = [
        r for r in recommendations
        if not cats or str(r.get("category", "")).upper() in cats
    ] or recommendations[:4]
    lines = []
    for rec in relevant[:5]:
        sev = rec.get("severity", "LOW")
        title = rec.get("title") or rec.get("recommendation", "")
        score_gain = rec.get("expected_score_gain", "")
        lines.append(
            f"  [{sev}] {title}"
            + (f" (expected gain: +{score_gain})" if score_gain else "")
        )
    return "\n".join(lines)


def _technology_digest(session: "EvaluationSession") -> str:
    intel = session.repository_intelligence
    parts = []

    # Use technology_detections if available (includes confidence + category)
    tech_detections = getattr(intel, "technology_detections", [])
    if tech_detections:
        languages = [t for t in tech_detections if t.get("category") == "LANGUAGE"]
        frameworks = [t for t in tech_detections if t.get("category") == "FRAMEWORK"]
        ml_tools = [t for t in tech_detections if t.get("category") == "ML"]
        databases = [t for t in tech_detections if t.get("category") == "DATABASE"]
        tools = [t for t in tech_detections if t.get("category") not in ("LANGUAGE", "FRAMEWORK", "ML", "DATABASE")]

        def fmt(techs):
            return ", ".join(
                f"{t['name']}{'@'+t['version'] if t.get('version') else ''} ({int(t.get('confidence', 1.0)*100)}%)"
                for t in techs[:6]
            )

        if languages:
            parts.append(f"  Languages:    {fmt(languages)}")
        if frameworks:
            parts.append(f"  Frameworks:   {fmt(frameworks)}")
        if ml_tools:
            parts.append(f"  ML/AI:        {fmt(ml_tools)}")
        if databases:
            parts.append(f"  Databases:    {fmt(databases)}")
        if tools:
            parts.append(f"  Tools:        {fmt(tools[:4])}")
    elif intel.detected_technologies:
        parts.append(f"  Detected Technologies: {', '.join(intel.detected_technologies[:12])}")

    tech_graph = intel.technology_graph
    if tech_graph and isinstance(tech_graph, dict):
        nodes = tech_graph.get("nodes") or []
        edges = tech_graph.get("edges") or []
        if nodes:
            parts.append(f"  Technology Graph: {len(nodes)} nodes, {len(edges)} relationships")

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Primary digest builder — uses EvaluationSession as source of truth
# ─────────────────────────────────────────────────────────────────────────────

def _build_repository_intelligence_digest(session: "EvaluationSession", agent: str) -> str:
    """
    Build a rich, structured context digest from the immutable EvaluationSession.
    This is the primary evidence injected into every code-aware agent prompt.
    """
    intel = session.repository_intelligence
    lines: list[str] = [
        f"SESSION-CONTEXT-ID: {session.session_fingerprint}",
        "",
        "=== REPOSITORY INTELLIGENCE (Static Analysis Output) ===",
        "",
    ]

    # 1. Health Metrics — every agent sees this
    health_str = _format_health(intel.health_metrics)
    if health_str:
        lines.append("HEALTH METRICS:")
        lines.append(health_str)
        lines.append("")

    # 2. Repository summary
    if intel.repository_summary:
        lines.append(f"REPOSITORY SUMMARY: {intel.repository_summary}")
        lines.append("")

    # 3. Technology Stack — technical, innovation agents
    if agent in ("technical", "innovation", "chief", "narrative"):
        tech_str = _technology_digest(session)
        if tech_str:
            lines.append("TECHNOLOGY STACK:")
            lines.append(tech_str)
            lines.append("")

    # 4. Architecture — technical, innovation, risk agents
    if agent in ("technical", "innovation", "risk", "chief", "narrative"):
        arch_str = _format_architecture(intel.architecture)
        if arch_str:
            lines.append("ARCHITECTURE:")
            lines.append(arch_str)
            lines.append("")

    # 5. Complexity Metrics — technical, risk agents
    if agent in ("technical", "risk"):
        metrics_str = _format_metrics(intel.complexity_metrics)
        if metrics_str:
            lines.append("COMPLEXITY METRICS:")
            lines.append(metrics_str)
            lines.append("")

    # 6. Dependencies — security, risk agents
    if agent in ("security", "risk", "technical", "chief", "narrative"):
        dep_str = _format_dependencies(intel.dependency_graph)
        if dep_str:
            lines.append("DEPENDENCIES:")
            lines.append(dep_str)
            lines.append("")

    # 7. Security Findings — security, risk agents
    if agent in ("security", "risk"):
        sec_str = _format_security_findings(intel.security_findings)
        lines.append("SECURITY FINDINGS:")
        lines.append(sec_str)
        lines.append("")

    # 8. Evidence records — agent-specific filtered view
    evidence_str = _format_evidence(intel.evidence, agent)
    if evidence_str:
        lines.append("STATIC ANALYSIS EVIDENCE:")
        lines.append(evidence_str)
        lines.append("")

    # 9. Recommendations — agent-specific filtered view
    if intel.recommendations:
        rec_str = _format_recommendations(intel.recommendations, agent)
        if rec_str:
            lines.append("AUTOMATED RECOMMENDATIONS:")
            lines.append(rec_str)
            lines.append("")

    # 10. Repository tree summary — technical agent
    if agent in ("technical",) and intel.repository_tree:
        tree_files = [
            node.get("path") or node.get("name")
            for node in intel.repository_tree[:20]
            if isinstance(node, dict) and node.get("type") == "file"
        ]
        if tree_files:
            lines.append("REPOSITORY TREE SAMPLE (top 20 files):")
            lines.append("  " + "\n  ".join(str(f) for f in tree_files))
            lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy fallback digest — used when no EvaluationSession is available
# (non-repository evaluations: PDF-only, description-only)
# ─────────────────────────────────────────────────────────────────────────────

def _legacy_code_intelligence_digest(ctx: dict[str, Any]) -> str:
    """
    Fallback digest from old parser keys.
    Used ONLY when no EvaluationSession/Repository Intelligence is available
    (i.e., non-GitHub project evaluations).
    """
    code = ctx.get("code_reader") or {}
    arch = ctx.get("architecture") or {}
    evidence = ctx.get("technical_evidence") or {}
    detection = ctx.get("project_type_detection") or {}
    if not any((code, arch, evidence, detection)):
        return "[No code intelligence — non-repository evaluation]"
    lines = [
        "Code Reader Summary:",
        code.get("summary", ""),
        "Detected Technologies: " + ", ".join(
            evidence.get("detected_technologies", []) or code.get("frameworks", []) or []
        ),
        "Architecture: " + arch.get("summary", ""),
    ]
    return "\n".join(line for line in lines if line.strip())


def _legacy_repository_intelligence_digest(ctx: dict[str, Any], agent: str) -> str:
    """
    Legacy formatter for repository intelligence dictionary.
    Used ONLY when no EvaluationSession is available.
    """
    intel = ctx.get("repository_intelligence")
    if not intel:
        return ""
        
    lines = ["\n### STRUCTURED REPOSITORY INTELLIGENCE DETECTED:"]
    
    # 1. Health Scores
    health = intel.get("health") or {}
    if health:
        lines.append(f"- Overall Codebase Health: {health.get('overall', health.get('overall_score', 0))}/100")
        lines.append(f"  * Documentation Health: {health.get('documentation', 0)}/100")
        lines.append(f"  * Testing Health: {health.get('testing', 0)}/100")
        lines.append(f"  * Security Health: {health.get('security', 0)}/100")
        lines.append(f"  * Code Quality Health: {health.get('code_quality', 0)}/100")
        
    # 2. Technology & Architecture Graphs
    if agent in ("technical", "innovation", "chief", "narrative"):
        tech_graph = intel.get("technology_graph") or {}
        if tech_graph.get("nodes"):
            techs = [node.get("label") or node.get("id") or "" for node in tech_graph.get("nodes", []) if node.get("type") == "technology"]
            techs = [str(t) for t in techs if t]
            if techs:
                lines.append(f"- Detected Tech Stack Nodes: {', '.join(techs)}")
        arch_graph = intel.get("architecture_graph") or {}
        if arch_graph.get("nodes"):
            layers = [node.get("label") or node.get("id") or "" for node in arch_graph.get("nodes", []) if node.get("type") == "layer"]
            layers = [str(l) for l in layers if l]
            if layers:
                lines.append(f"- Inferred Architecture Layers: {', '.join(layers)}")
                
    # 3. Dependency Warnings
    if agent in ("security", "risk", "chief", "narrative"):
        dep_graph = intel.get("dependency_graph") or {}
        warnings = dep_graph.get("warnings") or []
        if warnings:
            lines.append("- Outdated/Vulnerable Dependency Signals:")
            for w in warnings[:6]:
                lines.append(f"  * {w.get('package')} ({w.get('current_version')}) -> {w.get('warning_type')}: {w.get('message')}")
                
    # 4. Complexity & Metrics
    metrics = intel.get("metrics") or {}
    if metrics:
        total_loc = sum(m.get("loc", 0) for m in metrics.values() if isinstance(m, dict))
        avg_maintainability = sum(m.get("maintainability_index", 100) for m in metrics.values() if isinstance(m, dict)) / (len(metrics) or 1)
        lines.append("- Codebase Metrics Summary:")
        lines.append(f"  * Total Lines of Code (LOC): {total_loc}")
        lines.append(f"  * Average Maintainability Index: {avg_maintainability:.1f}/100")
        
    # 5. Evidence Records & Code Traces
    evidence = intel.get("evidence") or []
    if evidence:
        lines.append("- Traceable Static Analysis Evidence:")
        for ev in evidence:
            rule_id = ev.get("rule_id", "")
            is_relevant = False
            if agent == "technical" and any(x in rule_id for x in ("FASTAPI", "SQLALCHEMY", "TREE", "METRICS")):
                is_relevant = True
            elif agent == "security" and any(x in rule_id for x in ("SECRET", "UNSAFE_API", "VULNERABILITY", "JWT")):
                is_relevant = True
            elif agent == "risk" and any(x in rule_id for x in ("AUTHENTICATION", "GATEWAY", "CELERY")):
                is_relevant = True
            elif agent in ("innovation", "chief", "narrative"):
                is_relevant = True
                
            if is_relevant:
                lines.append(f"  * [Evidence] File: {ev.get('file_path')} | Rule: {rule_id} | Confidence: {int(ev.get('confidence', 0)*100)}%")
                
    # 6. Recommendations
    recommendations = intel.get("recommendations") or []
    if recommendations:
        lines.append("- Auto-Generated Recommendations:")
        for rec in recommendations:
            is_relevant = False
            category = rec.get("category", "")
            if agent == "technical" and category in ("IMPLEMENTATION", "ARCHITECTURE", "TESTING"):
                is_relevant = True
            elif agent == "security" and category == "SECURITY":
                is_relevant = True
            elif agent == "risk" and category in ("RISK", "SECURITY"):
                is_relevant = True
            elif agent in ("innovation", "chief", "narrative"):
                is_relevant = True
                
            if is_relevant:
                lines.append(f"  * [{rec.get('severity', 'LOW')}] {rec.get('title')}: {rec.get('recommendation')} (Expected Score Gain: +{rec.get('expected_score_gain', 1.0)})")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def slice_context_for_agent(
    ctx: dict[str, Any],
    agent: str,
    session: Optional["EvaluationSession"] = None,
) -> str:
    """
    Build a deterministic, agent-specific context digest.

    When an EvaluationSession is provided, Repository Intelligence is the
    PRIMARY source of all code knowledge. ctx is used only for non-code
    supplementary context (GitHub metadata, PDF, PPT, project description).

    When no session is provided (non-repository evaluation), falls back
    to the legacy code_reader/architecture/technical_evidence keys.
    """
    # Retrieve session from ctx if not passed directly
    if session is None:
        session = ctx.get("evaluation_session")

    brief_parts: list[str] = [
        f"Project: {ctx.get('project_name', 'Unknown')}",
        f"PROJECT_TYPE: {ctx.get('project_type', 'Hackathon Project')}",
    ]

    has_session = session is not None and bool(
        session.repository_intelligence.repository_tree
        or session.repository_intelligence.evidence
        or session.repository_intelligence.health_metrics
    )

    if agent == "presentation":
        # Presentation agent needs documents, not code intelligence
        brief_parts.append(_doc_digest(ctx))

    elif has_session:
        # All code-aware agents use EvaluationSession as the primary source
        if agent in ("technical", "security", "innovation", "risk"):
            brief_parts.append(_gh_excerpt(ctx, readme_limit=600))
        ri_digest = _build_repository_intelligence_digest(session, agent)
        brief_parts.append(ri_digest)

    else:
        # Non-repository evaluation fallback
        if agent == "technical":
            brief_parts.append(_gh_excerpt(ctx, readme_limit=1000))
            brief_parts.append(_legacy_code_intelligence_digest(ctx))
        elif agent == "security":
            sec = ctx.get("security") or {}
            risk_level = sec.get("risk_level", "N/A")
            sec_summary = sec.get("summary", "")[:400]
            brief_parts.append(f"Security Risk: {risk_level}\n{sec_summary}")
            brief_parts.append(_legacy_code_intelligence_digest(ctx))
        elif agent == "innovation":
            brief_parts.append((ctx.get("description") or "")[:400])
            brief_parts.append(_legacy_code_intelligence_digest(ctx))
        elif agent == "risk":
            brief_parts.append((ctx.get("description") or "")[:350])
            brief_parts.append(_legacy_code_intelligence_digest(ctx))
        else:
            brief_parts.append(_gh_excerpt(ctx, readme_limit=600))
            brief_parts.append(_doc_digest(ctx))
            brief_parts.append(_legacy_code_intelligence_digest(ctx))
            
        # Append structured repository intelligence digest to the agent slice if present in ctx
        intel_digest = _legacy_repository_intelligence_digest(ctx, agent)
        if intel_digest:
            brief_parts.append(intel_digest)

    text = "\n\n".join(p for p in brief_parts if p and p.strip())

    return truncate_text(text, MAX_AGENT_DIGEST_CHARS, label=f"digest:{agent}")


def truncate_brief(brief_text: str) -> str:
    return truncate_text(brief_text, MAX_BRIEF_CHARS, label="brief")
