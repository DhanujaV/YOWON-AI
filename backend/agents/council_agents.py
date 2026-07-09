"""Council agents - single-pass JSON evaluators for local Ollama."""

from crewai import Agent



from llm_utils import get_crewai_llm, get_model_name
from logging_config import get_logger

logger = get_logger(__name__)

from eval_context.prompt_registry import get_template_and_meta

_COMMON = get_template_and_meta("common_rules")["template"]


def _agent(
    label: str,
    role: str,
    goal: str,
    backstory: str,
    *,
    use_fallback: bool = False,
) -> Agent:
    model_name = get_model_name("specialist", use_fallback=use_fallback)
    logger.info("[%s] Agent initialized model=%s", label, model_name)
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory + "\n" + _COMMON,
        llm=get_crewai_llm("specialist", use_fallback=use_fallback),
        verbose=False,
        allow_delegation=False,
        max_iter=3,
        max_execution_time=600,
    )


def create_technical_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "FORGE",
        "Principal Software Engineer",
        "Return JSON with technical_score, strengths, weaknesses, risks, confidence.",
        get_template_and_meta("technical_agent")["template"],
        use_fallback=use_fallback,
    )


def create_security_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "SENTINEL",
        "Application Security Auditor",
        "Return JSON with security_score, risk_level, critical_findings, confidence.",
        get_template_and_meta("security_agent")["template"],
        use_fallback=use_fallback,
    )


def create_innovation_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "VISIONARY",
        "Technology Innovation Analyst",
        "Return JSON with innovation_score, scalability_score, differentiators, scalability_risk, confidence.",
        get_template_and_meta("innovation_agent")["template"],
        use_fallback=use_fallback,
    )


def create_presentation_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "SHOWCASE",
        "Pitch Coach",
        "Return JSON with presentation_score, strengths, improvements, confidence.",
        get_template_and_meta("presentation_agent")["template"],
        use_fallback=use_fallback,
    )


def create_risk_agent(*, use_fallback: bool = False) -> Agent:
    return _agent(
        "GUARDIAN",
        "Deployment Risk Analyst",
        "Return JSON with impact_score, failure_modes, top_risks, confidence.",
        get_template_and_meta("risk_agent")["template"],
        use_fallback=use_fallback,
    )
