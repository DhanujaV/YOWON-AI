"""CrewAI/Ollama integration checks for CrewAI 1.14.x."""

from typing import Any

from crewai import Agent, BaseLLM, Crew, Process, Task

from agents.insight_agent import create_insight_agent
from agents.council_agents import (
    create_innovation_agent,
    create_presentation_agent,
    create_risk_agent,
    create_security_agent,
    create_technical_agent,
)
from health_check import run_preflight_checks
from llm_utils import get_crewai_llm, get_model_name


def test_crewai_llm_initialization_returns_basellm():
    llm = get_crewai_llm("specialist")
    assert isinstance(llm, BaseLLM)
    model = llm.model
    assert model.startswith("ollama/") or model == get_model_name("specialist")
    assert get_model_name("specialist") in model


def test_council_agents_use_crewai_basellm():
    agents = [
        create_technical_agent(),
        create_security_agent(),
        create_innovation_agent(),
        create_presentation_agent(),
        create_risk_agent(),
    ]
    assert all(isinstance(agent, Agent) for agent in agents)
    assert all(isinstance(agent.llm, BaseLLM) for agent in agents)


def test_insight_agent_uses_crewai_basellm():
    agent = create_insight_agent()
    assert isinstance(agent, Agent)
    assert isinstance(agent.llm, BaseLLM)


def test_preflight_validates_ollama_model_llm_and_agents(monkeypatch):
    import health_check

    monkeypatch.setattr(
        health_check,
        "_ollama_tags",
        lambda: [get_model_name("specialist"), get_model_name("chief")],
    )
    monkeypatch.setattr(
        health_check.httpx.Client,
        "get",
        lambda self, url: type("Resp", (), {"raise_for_status": lambda self: None})(),
    )

    report = run_preflight_checks()
    assert report.ok is True
    assert not report.errors


class FakeCrewLLM(BaseLLM):
    model: str = "fake/test"

    def call(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[Any] | None = None,
    ) -> str:
        return "Final Answer: CrewAI integration healthy"


def test_end_to_end_crewai_kickoff_with_basellm():
    agent = Agent(
        role="CrewAI Integration Tester",
        goal="Return a short health confirmation.",
        backstory="You validate the agent execution path.",
        llm=FakeCrewLLM(model="fake/test"),
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    task = Task(
        description="Confirm CrewAI can execute a task with a BaseLLM.",
        expected_output="A health confirmation.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    assert "healthy" in str(result).lower()
