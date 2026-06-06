"""Narrative Agent — generates executive narrative from computed scores."""

from crewai import Agent
from config import CHIEF_MAX_EXECUTION_TIME
from llm_utils import get_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)

NARRATIVE_BACKSTORY = """
You are the Narrative Officer. You synthesize pre-computed numeric scores and
specialist key findings into concise narrative outputs: executive_summary,
top_strengths, top_weaknesses, recommended_fixes, deployment_roadmap.
Do NOT compute or change any numeric scores, verdicts, or risk levels.
Output ONLY a single JSON object. No markdown or extra text.
"""


def create_narrative_agent(*, use_fallback: bool = False) -> Agent:
    model_name = get_model_name("chief", use_fallback=use_fallback)
    logger.info("Narrative model: %s (use_fallback=%s)", model_name, use_fallback)
    return Agent(
        role="Narrative Officer",
        goal="Generate executive_summary, top_strengths, top_weaknesses, recommended_fixes, deployment_roadmap.",
        backstory=NARRATIVE_BACKSTORY,
        llm=get_llm("chief", use_fallback=use_fallback),
        verbose=False,
        allow_delegation=False,
        max_iter=1,
        max_execution_time=CHIEF_MAX_EXECUTION_TIME,
    )
