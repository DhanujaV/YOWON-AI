"""Chief Evaluation Agent — synthesis and deployment verdict."""

from crewai import Agent
from config import CHIEF_MAX_EXECUTION_TIME
from llm_utils import get_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)

CHIEF_BACKSTORY = """
You are the Chief Evaluation Officer. You synthesize specialist jury reports into
an executive deployment recommendation. Scores are pre-computed — do not change them.
Be concise, objective, and actionable.
CRITICAL: Output ONLY a single JSON object. No markdown fences. No prose before or after.
No think or redacted_thinking tags. Start with { end with }.
Do not use tools. One response only.
"""


def create_chief_evaluation_agent(*, use_fallback: bool = False) -> Agent:
    model_name = get_model_name('chief', use_fallback=use_fallback)
    logger.info('Chief model: %s (use_fallback=%s)', model_name, use_fallback)
    return Agent(
        role="Chief Evaluation Officer",
        goal="Generate executive_summary, strengths, weaknesses, recommended_fixes, deployment_roadmap.",
        backstory=CHIEF_BACKSTORY,
        llm=get_llm("chief", use_fallback=use_fallback),
        verbose=False,
        allow_delegation=False,
        # Single-pass LLM for narrative synthesis; allow longer execution time
        max_iter=3,
        max_execution_time=CHIEF_MAX_EXECUTION_TIME,
    )
