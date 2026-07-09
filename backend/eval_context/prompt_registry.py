"""
prompt_registry.py — Prompt Template Registry for YOWON AI.

Exposes prompt templates with explicit semantic versions and SHA-256 integrity hashes.
Ensures any change to prompt templates invalidates the evaluation cache automatically.
"""
from __future__ import annotations

import hashlib
from typing import Dict


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates with Semantic Versioning
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "common_rules": {
        "version": "1.0.0",
        "template": (
            "Evaluate ONLY evidence in the input. Never invent files, metrics, or competitors.\n"
            "If evidence is missing, lower confidence below 0.5 and note in weaknesses.\n"
            "Apply the supplied PROJECT_TYPE rubric. Do not impose enterprise expectations on academic or prototype work.\n"
            "Use the full 0-100 scale: 50 is limited/average, 70 is good, and 90+ requires exceptional evidence.\n"
            "Output ONLY valid JSON. No markdown. No reasoning preamble. No think tags.\n"
            "Start your response with { and end with }.\n"
            "Do not use tools. Do not ask questions. One response only.\n"
        )
    },
    "technical_agent": {
        "version": "1.0.0",
        "template": (
            "Principal Software Engineer. Goal: Assess architecture, code quality, and deployment readiness.\n"
            "You evaluate codebase modularity, styling paradigms, test presence, and frameworks from static analysis evidence.\n"
        )
    },
    "security_agent": {
        "version": "1.0.0",
        "template": (
            "Application Security Auditor. Goal: Audit OWASP risks, secrets, and dependency issues from static scan data.\n"
            "You analyze security findings, severity, and package dependencies. Treat None (missing) and [] (clean) scans distinctly.\n"
        )
    },
    "innovation_agent": {
        "version": "1.0.0",
        "template": (
            "Technology Innovation Analyst. Goal: Assess novelty, differentiation, and scale readiness.\n"
            "You look for AI, ML, or unique engineering differentiators in the technology graph.\n"
        )
    },
    "presentation_agent": {
        "version": "1.0.0",
        "template": (
            "Pitch Coach. Goal: Evaluate pitch clarity, problem/solution narrative, and deck quality.\n"
            "You assess PDF documentation, slides, and readability/presentation metrics.\n"
        )
    },
    "risk_agent": {
        "version": "1.0.0",
        "template": (
            "Deployment Risk Analyst. Goal: Predict real-world impact and failure modes under production stress.\n"
            "You analyze complexity, missing error handling, and runtime risks based on dependency and file metrics.\n"
        )
    },
    "technical_task": {
        "version": "1.0.0",
        "template": (
            "Brief:\n{brief}\n\nEvidence:\n{digest}\n\n"
            "Return JSON:\n{{\n"
            "  \"technical_score\": <int 0-100>,\n"
            "  \"strengths\": [\"...\", \"...\", \"...\"],\n"
            "  \"weaknesses\": [\"...\", \"...\", \"...\"],\n"
            "  \"risks\": [\"...\", \"...\", \"...\"],\n"
            "  \"confidence\": <0.0-1.0>\n"
            "}}\n"
        )
    },
    "security_task": {
        "version": "1.0.0",
        "template": (
            "Brief:\n{brief}\n\nStatic security evidence:\n{digest}\n\n"
            "Return JSON:\n{{\n"
            "  \"security_score\": <int 0-100>,\n"
            "  \"risk_level\": \"LOW\"|\"MEDIUM\"|\"HIGH\"|\"CRITICAL\",\n"
            "  \"critical_findings\": [\"...\", \"...\"],\n"
            "  \"confidence\": <0.0-1.0>\n"
            "}}\n"
        )
    },
    "innovation_task": {
        "version": "1.0.0",
        "template": (
            "Brief:\n{brief}\n\nEvidence:\n{digest}\n\n"
            "Return JSON:\n{{\n"
            "  \"innovation_score\": <int 0-100>,\n"
            "  \"scalability_score\": <int 0-100>,\n"
            "  \"differentiators\": [\"...\", \"...\", \"...\"],\n"
            "  \"scalability_risk\": \"<one sentence>\",\n"
            "  \"confidence\": <0.0-1.0>\n"
            "}}\n"
        )
    },
    "presentation_task": {
        "version": "1.0.0",
        "template": (
            "Brief:\n{brief}\n\nPresentation materials:\n{digest}\n"
            "If no deck, PDF, or documentation exists, return explicitly:\n"
            "{{\n"
            "    \"presentation_score\": 0,\n"
            "    \"status\": \"INSUFFICIENT_EVIDENCE\",\n"
            "    \"strengths\": [],\n"
            "    \"improvements\": [],\n"
            "    \"confidence\": 0.0\n"
            "}}\n"
            "Otherwise return JSON:\n"
            "{{\n"
            "    \"presentation_score\": <int 0-100>,\n"
            "    \"strengths\": [\"...\", \"...\", \"...\"],\n"
            "    \"improvements\": [\"...\", \"...\", \"...\"],\n"
            "    \"confidence\": <0.0-1.0>\n"
            "}}\n"
        )
    },
    "risk_task": {
        "version": "1.0.0",
        "template": (
            "Brief:\n{brief}\n\nContext:\n{digest}\n\n"
            "Return JSON:\n{{\n"
            "  \"impact_score\": <int 0-100>,\n"
            "  \"failure_modes\": [\"...\", \"...\", \"...\", \"...\", \"...\"],\n"
            "  \"top_risks\": [\"...\", \"...\", \"...\", \"...\", \"...\"],\n"
            "  \"confidence\": <0.0-1.0>\n"
            "}}\n"
        )
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_template_and_meta(name: str) -> Dict[str, str]:
    """Returns template text, version, and SHA256 hash for a registered prompt template."""
    info = PROMPT_TEMPLATES.get(name)
    if not info:
        raise KeyError(f"Prompt template '{name}' is not registered in prompt_registry.py")
    
    text = info["template"]
    version = info["version"]
    template_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    
    return {
        "template": text,
        "version": version,
        "hash": template_hash
    }


def get_prompt_registry_hash() -> str:
    """Computes a single combined SHA256 hash of all registered prompt templates for cache validation."""
    combined = "".join(
        f"{name}:{info['version']}:{hashlib.sha256(info['template'].encode('utf-8')).hexdigest()}"
        for name, info in sorted(PROMPT_TEMPLATES.items())
    )
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def get_all_template_metadata() -> Dict[str, Dict[str, str]]:
    """Returns a dictionary containing version and hash for every prompt template."""
    res = {}
    for name in PROMPT_TEMPLATES:
        meta = get_template_and_meta(name)
        res[name] = {
            "version": meta["version"],
            "hash": meta["hash"]
        }
    return res
