"""Specialist jury agents — single-pass JSON evaluators for local Ollama."""

from crewai import Agent

from config import AGENT_MAX_EXECUTION_TIME, AGENT_MAX_ITER
from llm_utils import get_llm

_COMMON = """
Evaluate ONLY evidence in the input. Never invent files, metrics, or competitors.
If evidence is missing, lower confidence below 0.5 and note in weaknesses.
Apply the supplied PROJECT_TYPE rubric. Do not impose enterprise expectations on academic or prototype work.
Use the full 0-100 scale: 50 is limited/average, 70 is good, and 90+ requires exceptional evidence.
Output ONLY valid JSON. No markdown. No reasoning preamble. No think tags.
Start your response with { and end with }.
Do not use tools. Do not ask questions. One response only.
"""


def _agent(
    role: str,
    goal: str,
    backstory: str,
    *,
    use_fallback: bool = False,
) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory + _COMMON,
        llm=get_llm("specialist", use_fallback=use_fallback),
        verbose=False,
        allow_delegation=False,
        # Enforce single-pass, long-running allowance for specialists
        max_iter=3,
        max_execution_time=600,
    )


def create_technical_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "Principal Software Engineer",
        "Return JSON with technical_score, strengths, weaknesses, risks, confidence.",
        "You assess architecture, code quality, and deployment readiness.",
        use_fallback=use_fallback,
    )


def create_security_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "Application Security Auditor",
        "Return JSON with security_score, risk_level, critical_findings, confidence.",
        "You audit OWASP risks, secrets, and dependency issues from static scan data.",
        use_fallback=use_fallback,
    )


def create_innovation_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "Technology Innovation Analyst",
        "Return JSON with innovation_score, scalability_score, differentiators, scalability_risk, confidence.",
        "You assess novelty, differentiation, and scale readiness.",
        use_fallback=use_fallback,
    )


def create_presentation_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "Pitch Coach",
        "Return JSON with presentation_score, strengths, improvements, confidence.",
        "You evaluate pitch clarity, problem/solution narrative, and deck quality.",
        use_fallback=use_fallback,
    )


def create_risk_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "Deployment Risk Analyst",
        "Return JSON with impact_score, failure_modes, top_risks, confidence.",
        "You predict real-world impact and failure modes under production stress.",
        use_fallback=use_fallback,
    )
