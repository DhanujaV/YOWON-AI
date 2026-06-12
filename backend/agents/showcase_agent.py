"""
agents/showcase_agent.py

Showcase agent

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_crewai_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)


PPT_AGENT_BACKSTORY = """
You are a startup pitch coach and presentation evaluator.

You assess:
- Problem clarity
- Solution clarity
- Technical presentation
- Market validation
- Feasibility
- Presentation quality

Your feedback is concise, practical, and actionable.
"""


PPT_AGENT_GOAL = """
Evaluate the project presentation and provide:

PRESENTATION SCORE: [0-100]

PROBLEM STATEMENT:
Good / Average / Poor

SOLUTION CLARITY:
Good / Average / Poor

ARCHITECTURE EXPLANATION:
Good / Average / Poor

MARKET VALIDATION:
Good / Average / Poor

FEASIBILITY:
Good / Average / Poor

TOP 3 IMPROVEMENTS:
- ...
- ...
- ...

Maximum 200 words.
"""


def create_showcase_agent() -> Agent:
    logger.info("[SHOWCASE] Agent initialized model=%s", get_model_name("specialist"))
    return Agent(
        role="Pitch Coach & Presentation Evaluator",
        goal=PPT_AGENT_GOAL,
        backstory=PPT_AGENT_BACKSTORY,
        llm=get_crewai_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )
