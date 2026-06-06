"""CrewAI tasks — JSON via prompts; parsed in crew.py (not CrewAI output_json)."""

from __future__ import annotations

from crewai import Agent, Task
import json

from eval_context.context_slicer import truncate_brief, truncate_text
from config import MAX_AGENT_DIGEST_CHARS

_JSON_RULES = """
Score anchors: 90-100 exceptional for the supplied project type | 80-89 excellent |
70-79 good | 60-69 average | below 60 needs improvement.
Missing evidence is not proof of quality. Do not award 90+ without exceptional evidence.
Max 15 words per string field. JSON only — no markdown fences. No thinking tags.
Your entire response must be one JSON object starting with { and ending with }.
"""


def _prep(brief: str, digest: str) -> tuple[str, str]:
    return truncate_brief(brief), truncate_text(digest, MAX_AGENT_DIGEST_CHARS, label="evidence")


def create_technical_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    return Task(
        description=f"""
Brief:
{brief}

Evidence:
{digest}

Return JSON:
{{
  "technical_score": <int 0-100>,
  "strengths": ["...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "risks": ["...", "...", "..."],
  "confidence": <0.0-1.0>
}}
{_JSON_RULES}
""",
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_security_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    return Task(
        description=f"""
Brief:
{brief}

Static security evidence:
{digest}

Return JSON:
{{
  "security_score": <int 0-100>,
  "risk_level": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL",
  "critical_findings": ["...", "..."],
  "confidence": <0.0-1.0>
}}
{_JSON_RULES}
""",
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_innovation_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    return Task(
        description=f"""
Brief:
{brief}

Evidence:
{digest}

Return JSON:
{{
  "innovation_score": <int 0-100>,
  "scalability_score": <int 0-100>,
  "differentiators": ["...", "...", "..."],
  "scalability_risk": "<one sentence>",
  "confidence": <0.0-1.0>
}}
{_JSON_RULES}
""",
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_presentation_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    return Task(
        description=f"""
Brief:
{brief}

Presentation materials:
{digest}
If no deck, PDF, or documentation exists, return explicitly:
{{
    "presentation_score": 0,
    "status": "INSUFFICIENT_EVIDENCE",
    "strengths": [],
    "improvements": [],
    "confidence": 0.0
}}

Otherwise return JSON:
{{
    "presentation_score": <int 0-100>,
    "strengths": ["...", "...", "..."],
    "improvements": ["...", "...", "..."],
    "confidence": <0.0-1.0>
}}
{_JSON_RULES}
""",
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_risk_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    return Task(
        description=f"""
Brief:
{brief}

Context:
{digest}

Return JSON:
{{
  "impact_score": <int 0-100>,
  "failure_modes": ["...", "...", "...", "...", "..."],
  "top_risks": ["...", "...", "...", "...", "..."],
  "confidence": <0.0-1.0>
}}
{_JSON_RULES}
""",
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_chief_evaluation_task(
    agent: Agent,
    specialist_summary: str,
    computed: dict,
) -> Task:
    import json

    # Chief only generates narrative synthesis. Scores are computed deterministically in Python.
    specialist_summary = specialist_summary[:3500]
    computed_json = json.dumps(computed, indent=2)
    description = (
        "You are the Chief Evaluation Officer. Do NOT change any numeric scores.\n"
        "Using the specialist reports below, produce only the following JSON fields:\n"
        "- executive_summary (2-3 sentences)\n"
        "- top_strengths (array of strings, max 5)\n"
        "- top_weaknesses (array of strings, max 5)\n"
        "- contradictions (array of strings)\n"
        "- blocking_issues (array of strings)\n"
        "- recommended_fixes (array of strings, max 5)\n"
        "- deployment_roadmap (array of strings, max 6)\n\n"
        "Specialist jury reports:\n"
        f"{specialist_summary}\n\n"
        "Pre-computed scores (for reference only, DO NOT MODIFY):\n"
        f"{computed_json}\n\n"
        "Return a single JSON object only. No markdown, no explanation. Start with { and end with }."
    )
    return Task(
        description=description,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_narrative_task(agent: Agent, numeric_summary: dict, key_findings: str) -> Task:
    # numeric_summary should contain overall_score, verdict, risk_level, agent_scores
    brief = json.dumps(numeric_summary)
    # keep the prompt small — numeric summary plus short findings
    user_text = (
        "Numeric summary:\n"
        + brief
        + "\n\nKey findings:\n"
        + (key_findings or "")[:800]
        + "\n\nReturn only a single JSON object with keys: executive_summary, top_strengths, top_weaknesses, recommended_fixes, deployment_roadmap."
    )
    return Task(
        description=user_text,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )
