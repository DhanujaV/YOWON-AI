"""
agents/engineering_agent.py

Engineering Agent

Combines:
1. Technical Evaluation
2. Security Evaluation

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_llm


ENGINEERING_AGENT_BACKSTORY = """
You are a Principal Software Engineer and Application Security Expert.

You evaluate:
- Software architecture
- Code quality
- Security posture
- Deployment readiness

You provide concise, evidence-based assessments and focus only on the most
important strengths, weaknesses, and security risks.
"""


ENGINEERING_AGENT_GOAL = """
Evaluate the project and provide:

TECHNICAL SCORE: [0-100]

SECURITY SCORE: [0-100]

TOP 3 STRENGTHS:
- ...

TOP 3 WEAKNESSES:
- ...

TOP 3 SECURITY RISKS:
- ...

RISK LEVEL:
LOW | MEDIUM | HIGH | CRITICAL

Maximum 250 words.
"""


def create_engineering_agent() -> Agent:
    return Agent(
        role="Principal Software Engineer & Application Security Expert",
        goal=ENGINEERING_AGENT_GOAL,
        backstory=ENGINEERING_AGENT_BACKSTORY,
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )