"""Manual health check for CrewAI Agent initialization."""

from __future__ import annotations

from crewai import BaseLLM

from agents.insight_agent import create_insight_agent
from agents.council_agents import (
    create_innovation_agent,
    create_presentation_agent,
    create_risk_agent,
    create_security_agent,
    create_technical_agent,
)


def main() -> None:
    factories = [
        ("FORGE", create_technical_agent),
        ("SENTINEL", create_security_agent),
        ("VISIONARY", create_innovation_agent),
        ("SHOWCASE", create_presentation_agent),
        ("GUARDIAN", create_risk_agent),
        ("INSIGHT", create_insight_agent),
    ]
    for label, factory in factories:
        agent = factory()
        if not isinstance(agent.llm, BaseLLM):
            raise TypeError(f"{label} llm is {type(agent.llm).__name__}, expected BaseLLM")
        print(f"[{label}] Agent initialized model={agent.llm.model}")
    print("CREWAI_AGENT_INITIALIZATION_OK")


if __name__ == "__main__":
    main()
