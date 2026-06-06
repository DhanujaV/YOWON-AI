"""
agents/ppt_agent.py

Presentation Evaluation Agent

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_llm


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


def create_ppt_agent() -> Agent:
    return Agent(
        role="Pitch Coach & Presentation Evaluator",
        goal=PPT_AGENT_GOAL,
        backstory=PPT_AGENT_BACKSTORY,
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )