"""
agents/risk_impact_agent.py

Risk & Impact Agent

Combines:
1. Real-World Impact Assessment
2. Failure Risk Assessment

Optimized for local Ollama models.
"""

from crewai import Agent
from llm_utils import get_llm


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


def create_risk_impact_agent() -> Agent:
    return Agent(
        role="Real-World Impact Analyst & Veteran CTO Failure Analyst",
        goal=RISK_IMPACT_AGENT_GOAL,
        backstory=RISK_IMPACT_AGENT_BACKSTORY,
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )