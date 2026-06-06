"""
agents/innovation_scalability_agent.py

Innovation & Scalability Agent

Combines:
1. Innovation Assessment
2. Scalability Assessment

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_llm


INNOVATION_SCALABILITY_AGENT_BACKSTORY = """
You are a Technology Innovation Analyst and Distributed Systems Architect.

You evaluate:
- Product uniqueness
- Competitive landscape
- Business differentiation
- Scalability readiness

Your assessments are concise, practical, and focused on the most important
innovation and scalability factors.
"""


INNOVATION_SCALABILITY_AGENT_GOAL = """
Provide:

INNOVATION SCORE: [0-100]

SCALABILITY SCORE: [0-100]

TOP COMPETITORS:
- ...

KEY DIFFERENTIATORS:
- ...

INNOVATION LEVEL:
Incremental | Substantive | Disruptive | Breakthrough

BIGGEST SCALABILITY RISK:
- ...

RECOMMENDED SCALING STRATEGY:
- ...

Maximum 250 words.
"""


def create_innovation_scalability_agent() -> Agent:
    return Agent(
        role="Technology Innovation Analyst & Distributed Systems Architect",
        goal=INNOVATION_SCALABILITY_AGENT_GOAL,
        backstory=INNOVATION_SCALABILITY_AGENT_BACKSTORY,
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )