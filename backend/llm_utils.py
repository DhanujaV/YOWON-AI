"""Ollama LLM factory, direct invocation, and retry."""

from __future__ import annotations

import time
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from config import (
    AGENT_MAX_RETRIES,
    AGENT_RETRY_DELAY_SEC,
    OLLAMA_CHIEF_MODEL,
    OLLAMA_CHIEF_NUM_PREDICT,
    OLLAMA_FALLBACK_MODEL,
    OLLAMA_FAST_MODEL,
    OLLAMA_HOST,
    OLLAMA_NUM_CTX,
    OLLAMA_SPECIALIST_MODEL,
    OLLAMA_SPECIALIST_NUM_PREDICT,
    OLLAMA_TEMPERATURE,
    CHIEF_MODEL_CHAIN,
)
from logging_config import get_logger

logger = get_logger(__name__)

CREW_ABORT_PHRASES = (
    "agent stopped due to iteration limit",
    "agent stopped due to time limit",
    "iteration limit or time limit",
    "max iterations reached",
    "execution timed out",
)


def is_crew_abort_output(raw: str) -> bool:
    if not raw:
        return True
    lower = raw.strip().lower()
    if len(lower) < 20 and "{" not in raw:
        return any(p in lower for p in CREW_ABORT_PHRASES)
    return any(p in lower for p in CREW_ABORT_PHRASES)


def get_llm(role: str = "specialist", *, use_fallback: bool = False) -> ChatOllama:
    profiles: dict[str, dict[str, Any]] = {
        "specialist": {
            "model": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_SPECIALIST_MODEL,
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_SPECIALIST_NUM_PREDICT,
        },
        "fast": {
            "model": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_FAST_MODEL,
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_SPECIALIST_NUM_PREDICT,
        },
        "chief": {
            "model": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_CHIEF_MODEL,
            "temperature": OLLAMA_TEMPERATURE,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_CHIEF_NUM_PREDICT,
        },
    }
    cfg = profiles.get(role, profiles["specialist"])
    return ChatOllama(base_url=OLLAMA_HOST, **cfg)


def get_model_name(role: str = "specialist", *, use_fallback: bool = False) -> str:
    profiles = {
        "specialist": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_SPECIALIST_MODEL,
        "fast": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_FAST_MODEL,
        "chief": OLLAMA_FALLBACK_MODEL if use_fallback else OLLAMA_CHIEF_MODEL,
    }
    return profiles.get(role, profiles["specialist"])


def invoke_direct_llm(
    *,
    role: str,
    system_prompt: str,
    user_prompt: str,
    label: str,
    project_id: str = "",
    use_fallback: bool = False,
) -> str:
    """Single-shot Ollama call with timing logs (bypasses CrewAI iteration loop)."""
    model_name = get_model_name(role, use_fallback=use_fallback)
    prompt_chars = len(system_prompt) + len(user_prompt)
    prefix = f"[{project_id[:8]}]" if project_id else ""

    logger.info(
        "%s LLM START %s model=%s prompt_chars=%d ctx_limit=%d num_predict=%s",
        prefix,
        label,
        model_name,
        prompt_chars,
        OLLAMA_NUM_CTX,
        OLLAMA_CHIEF_NUM_PREDICT if role == "chief" else OLLAMA_SPECIALIST_NUM_PREDICT,
    )

    llm = get_llm(role, use_fallback=use_fallback)
    t0 = time.perf_counter()
    try:
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.exception(
            "%s LLM FAIL %s after %.2fs model=%s — %s",
            prefix,
            label,
            elapsed,
            model_name,
            exc,
        )
        raise

    elapsed = time.perf_counter() - t0
    raw = response.content if hasattr(response, "content") else str(response)
    token_est = max(1, len(raw) // 4)
    logger.info(
        "%s LLM END %s in %.2fs model=%s response_chars=%d est_tokens=%d",
        prefix,
        label,
        elapsed,
        model_name,
        len(raw),
        token_est,
    )
    return str(raw)


def invoke_chief_with_chain(
    *,
    system_prompt: str,
    user_prompt: str,
    label: str,
    project_id: str = "",
    chain: str | None = None,
) -> str:
    """Try a chain of chief models. Return first non-empty response."""
    models = (chain or CHIEF_MODEL_CHAIN).split(",")
    last_exc = None
    for m in models:
        m = m.strip()
        try:
            # Temporarily override OLLAMA_CHIEF_MODEL by creating a ChatOllama instance
            logger.info("[%s] Chief try model=%s", project_id[:8], m)
            # call llm directly with chosen model name via ChatOllama
            llm = ChatOllama(base_url=OLLAMA_HOST, model=m, temperature=OLLAMA_TEMPERATURE, num_ctx=OLLAMA_NUM_CTX, num_predict=OLLAMA_CHIEF_NUM_PREDICT)
            t0 = time.perf_counter()
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            elapsed = time.perf_counter() - t0
            raw = response.content if hasattr(response, "content") else str(response)
            logger.info("[%s] Chief model=%s returned %d chars in %.2fs", project_id[:8], m, len(raw), elapsed)
            if raw and len(raw.strip()) > 0:
                return str(raw)
        except Exception as exc:
            last_exc = exc
            logger.warning("[%s] Chief model %s failed: %s", project_id[:8], m, exc)
            continue
    if last_exc:
        raise last_exc
    return ""


def invoke_with_retry(
    fn: Callable[[], str],
    *,
    label: str,
    project_id: str = "",
    model: str = "",
    max_retries: int = AGENT_MAX_RETRIES,
    fallback_fn: Callable[[], str] | None = None,
) -> str:
    """Run callable with backoff; optional fallback_fn on final attempt."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if attempt == max_retries and fallback_fn is not None and attempt > 0:
                logger.warning(
                    "[%s] %s using fallback model after %d failures",
                    project_id[:8] if project_id else "sys",
                    label,
                    attempt,
                )
                return fallback_fn()
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = AGENT_RETRY_DELAY_SEC * (attempt + 1)
            logger.warning(
                "[%s] %s attempt %d/%d failed: %s — retry in %.1fs",
                project_id[:8] if project_id else "sys",
                label,
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]
