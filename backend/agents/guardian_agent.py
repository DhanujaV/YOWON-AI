"""
agents/guardian_agent.py

Guardian agent

Combines:
1. Real-World Impact Assessment
2. Failure Risk Assessment

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_crewai_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)


RISK_IMPACT_AGENT_BACKSTORY = """
You are a Real-World Impact Analyst and Veteran CTO.

You evaluate:
- Social impact
- Business impact
- Ethical concerns
- Regulatory risks
- Project failure risks

Your analysis is concise, practical, and focused on the most important
real-world consequences.
"""


RISK_IMPACT_AGENT_GOAL = """
Provide:

IMPACT SCORE: [0-100]

POSITIVE IMPACT:
- ...

NEGATIVE IMPACT:
- ...

TOP 5 RISKS:
- ...
- ...
- ...
- ...
- ...

TOP 5 FAILURE MODES:
- ...
- ...
- ...
- ...
- ...

OVERALL RISK LEVEL:
LOW | MEDIUM | HIGH | CRITICAL

RECOMMENDED ACTIONS:
- ...
- ...
- ...

Maximum 300 words.
"""


def create_guardian_agent() -> Agent:
    logger.info("[GUARDIAN] Agent initialized model=%s", get_model_name("specialist"))
    return Agent(
        role="Real-World Impact Analyst & Veteran CTO Failure Analyst",
        goal=RISK_IMPACT_AGENT_GOAL,
        backstory=RISK_IMPACT_AGENT_BACKSTORY,
        llm=get_crewai_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )
