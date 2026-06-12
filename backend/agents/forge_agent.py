"""
agents/forge_agent.py

Forge agent

Combines:
1. Technical Evaluation
2. Security Evaluation

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_crewai_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)


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


def create_forge_agent() -> Agent:
    logger.info("[FORGE] Agent initialized model=%s", get_model_name("specialist"))
    return Agent(
        role="Principal Software Engineer & Application Security Expert",
        goal=ENGINEERING_AGENT_GOAL,
        backstory=ENGINEERING_AGENT_BACKSTORY,
        llm=get_crewai_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )
