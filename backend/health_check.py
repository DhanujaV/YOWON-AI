"""Pre-flight checks before starting an evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from crewai import BaseLLM

from config import (
    CHROMA_DIR,
    GITHUB_TOKEN,
    OLLAMA_CHIEF_MODEL,
    OLLAMA_HOST,
    OLLAMA_SPECIALIST_MODEL,
)
from logging_config import get_logger
from llm_utils import get_crewai_llm

logger = get_logger(__name__)


@dataclass
class HealthReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ollama_models: list[str] = field(default_factory=list)

    def raise_if_critical(self) -> None:
        if not self.ok:
            raise RuntimeError("; ".join(self.errors))


def _ollama_tags() -> list[str]:
    url = f"{OLLAMA_HOST.rstrip('/')}/api/tags"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return [m.get("name", "") for m in data.get("models", [])]


def _model_available(tags: list[str], wanted: str) -> bool:
    if not wanted:
        return False
    base = wanted.split(":")[0]
    for tag in tags:
        if tag == wanted or tag.startswith(f"{base}:"):
            return True
    return False


def run_preflight_checks(*, require_github: bool = False) -> HealthReport:
    report = HealthReport(ok=True)

    # Ollama reachable
    try:
        tags = _ollama_tags()
        report.ollama_models = tags
        logger.info("Ollama reachable at %s — models: %s", OLLAMA_HOST, tags)
    except Exception as exc:
        report.ok = False
        report.errors.append(f"Ollama not reachable at {OLLAMA_HOST}: {exc}")
        return report

    for label, model in (
        ("specialist", OLLAMA_SPECIALIST_MODEL),
        ("chief", OLLAMA_CHIEF_MODEL),
    ):
        if not _model_available(tags, model):
            report.ok = False
            report.errors.append(
                f"Ollama model {model!r} not found. Run: ollama pull {model}"
            )

    # CrewAI LLM and Agent construction
    try:
        specialist_llm = get_crewai_llm("specialist")
        chief_llm = get_crewai_llm("chief")
        if not isinstance(specialist_llm, BaseLLM):
            raise TypeError(f"specialist CrewAI LLM is {type(specialist_llm).__name__}, expected BaseLLM")
        if not isinstance(chief_llm, BaseLLM):
            raise TypeError(f"chief CrewAI LLM is {type(chief_llm).__name__}, expected BaseLLM")
        logger.info("CrewAI LLM objects valid: specialist=%s chief=%s", type(specialist_llm).__name__, type(chief_llm).__name__)
    except Exception as exc:
        report.ok = False
        report.errors.append(f"CrewAI LLM initialization failed: {exc}")
        return report

    try:
        from agents.insight_agent import create_insight_agent
        from agents.council_agents import (
            create_innovation_agent,
            create_presentation_agent,
            create_risk_agent,
            create_security_agent,
            create_technical_agent,
        )

        factories = (
            ("FORGE", create_technical_agent),
            ("SENTINEL", create_security_agent),
            ("VISIONARY", create_innovation_agent),
            ("SHOWCASE", create_presentation_agent),
            ("GUARDIAN", create_risk_agent),
            ("INSIGHT", create_insight_agent),
        )
        for label, factory in factories:
            agent = factory()
            if not isinstance(agent.llm, BaseLLM):
                raise TypeError(f"{label} Agent llm is {type(agent.llm).__name__}, expected BaseLLM")
            logger.info("[%s] Agent creation health check passed model=%s", label, getattr(agent.llm, "model", "unknown"))
    except Exception as exc:
        report.ok = False
        report.errors.append(f"CrewAI Agent creation failed: {exc}")
        return report

    # Chroma directory writable
    try:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        test_file = CHROMA_DIR / ".healthcheck"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except Exception as exc:
        report.ok = False
        report.errors.append(f"Chroma storage unavailable: {exc}")

    # GitHub (optional)
    if require_github and not GITHUB_TOKEN:
        report.warnings.append(
            "GITHUB_TOKEN not set — public repos only; rate limits may apply"
        )

    try:
        with httpx.Client(timeout=8.0) as client:
            client.get("https://api.github.com/zen")
    except Exception as exc:
        if require_github:
            report.warnings.append(f"GitHub API slow or unreachable: {exc}")

    return report
