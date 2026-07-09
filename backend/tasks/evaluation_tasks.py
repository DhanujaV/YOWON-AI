"""CrewAI tasks — JSON via prompts; parsed in crew.py (not CrewAI output_json)."""

from __future__ import annotations

import json
from crewai import Agent, Task

from eval_context.context_slicer import truncate_brief, truncate_text
from config import MAX_AGENT_DIGEST_CHARS
from eval_context.prompt_registry import get_template_and_meta

_JSON_RULES = get_template_and_meta("common_rules")["template"]


def _prep(brief: str, digest: str) -> tuple[str, str]:
    return truncate_brief(brief), truncate_text(digest, MAX_AGENT_DIGEST_CHARS, label="evidence")


def create_technical_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    template = get_template_and_meta("technical_task")["template"]
    description = template.format(brief=brief, digest=digest)
    return Task(
        description=description + "\n" + _JSON_RULES,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_security_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    template = get_template_and_meta("security_task")["template"]
    description = template.format(brief=brief, digest=digest)
    return Task(
        description=description + "\n" + _JSON_RULES,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_innovation_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    template = get_template_and_meta("innovation_task")["template"]
    description = template.format(brief=brief, digest=digest)
    return Task(
        description=description + "\n" + _JSON_RULES,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_presentation_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    template = get_template_and_meta("presentation_task")["template"]
    description = template.format(brief=brief, digest=digest)
    return Task(
        description=description + "\n" + _JSON_RULES,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_risk_task(agent: Agent, brief: str, digest: str) -> Task:
    brief, digest = _prep(brief, digest)
    template = get_template_and_meta("risk_task")["template"]
    description = template.format(brief=brief, digest=digest)
    return Task(
        description=description + "\n" + _JSON_RULES,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )


def create_chief_evaluation_task(
    agent: Agent,
    specialist_summary: str,
    computed: dict,
) -> Task:
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
        "- roadmap (array of strings, max 6; action items only, not one long string)\n"
        "- deployment_roadmap (same array as roadmap for backward compatibility)\n\n"
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
    user_text = (
        "Numeric summary:\n"
        + brief
        + "\n\nKey findings:\n"
        + (key_findings or "")[:800]
        + "\n\nCRITICAL MANDATE: You must never invent, modify, or output any scores, metrics, or ratings in the narrative content other than explaining the exact calibrated values provided in the Numeric Summary. Do not change, override, or invent new scores.\n"
        + "\nReturn only a single JSON object with keys: executive_summary, top_strengths, top_weaknesses, recommended_fixes, roadmap, deployment_roadmap. Roadmap fields must be arrays of full action-item strings, never a single string."
    )
    return Task(
        description=user_text,
        expected_output="Single JSON object only — no other text",
        agent=agent,
    )
