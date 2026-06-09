"""JSON extraction, repair, and validation helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from logging_config import get_logger
from validation.schemas import AgentScores, ChiefVerdict

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

# Score field required per agent model (reject partial JSON that omits scores)
AGENT_SCORE_FIELDS: dict[str, str] = {
    "TechnicalReport": "technical_score",
    "SecurityReport": "security_score",
    "InnovationReport": "innovation_score",
    "PresentationReport": "presentation_score",
    "RiskReport": "impact_score",
}

def _strip_thinking(text: str) -> str:
    """Remove reasoning blocks from qwen3 / think-tagged models."""
    cleaned = text
    for pattern in (
        r"<thinking>[\s\S]*?</thinking>",
        r"<think>[\s\S]*?</think>",
        r"<think>[\s\S]*?(?=\{|$)",
    ):
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()
    start = cleaned.find("{")
    if start > 0:
        return cleaned[start:].strip()
    return cleaned


def repair_json(text: str) -> str:
    """Attempt to fix common LLM JSON mistakes before parsing."""
    text = _strip_thinking(text)
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    # Only fix unquoted keys when clearly key-like (avoid breaking strings)
    text = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', text)
    return text


def log_raw_output(label: str, raw: str, *, max_chars: int = 600) -> None:
    preview = (raw or "").strip()
    if len(preview) > max_chars:
        preview = preview[:max_chars] + f"... [{len(raw)} chars total]"
    logger.info("[%s] Raw LLM output preview: %s", label, preview or "(empty)")


def extract_json(text: str, *, label: str = "agent") -> dict[str, Any] | None:
    """
    Parse the first JSON object from LLM output.
    Returns None on failure (never silently returns {}).
    """
    if not text or not str(text).strip():
        logger.error("[%s] JSON extraction failed — empty input", label)
        return None

    text = _strip_thinking(str(text))

    candidates: list[str] = []
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1).strip())
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        candidates.append(brace.group(0))

    if not candidates:
        print("\n" + "=" * 80)
        print("AGENT:", label)
        print("RAW OUTPUT:")
        print(text)
        print("=" * 80 + "\n")

        log_raw_output(label, text)
        
        logger.error("[%s] JSON extraction failed — no JSON object found in %d chars", label, len(text))
        return None

    last_error: str | None = None
    for candidate in candidates:
        for attempt_text in (candidate, repair_json(candidate)):
            try:
                parsed = json.loads(attempt_text)
                if not isinstance(parsed, dict):
                    last_error = f"expected object, got {type(parsed).__name__}"
                    continue
                if not parsed:
                    last_error = "empty object {}"
                    continue
                return parsed
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                continue

    log_raw_output(label, text)
    logger.error("[%s] JSON extraction failed — %s", label, last_error)
    return None


def _has_required_score(model: Type[BaseModel], data: dict[str, Any]) -> bool:
    field = AGENT_SCORE_FIELDS.get(model.__name__)
    if not field:
        return bool(data)
    val = data.get(field)
    return isinstance(val, (int, float)) and 0 <= int(val) <= 100


def parse_agent_json(
    raw: str,
    model: Type[T],
    fallback: dict[str, Any],
    *,
    label: str = "agent",
) -> tuple[T, str]:
    """
    Parse and validate agent JSON.

    Returns (report, source) where source is 'llm' | 'merged' | 'fallback'.
    """
    log_raw_output(label, raw)
    data = extract_json(raw, label=label)

    if data is None:
        logger.warning("[%s] Using explicit fallback — no parseable JSON", label)
        return model(**fallback), "fallback"

    if not _has_required_score(model, data):
        logger.warning(
            "[%s] Parsed JSON missing required score field — merge with fallback",
            label,
        )
        merged = {**fallback, **{k: v for k, v in data.items() if v is not None}}
        try:
            return model(**merged), "merged"
        except ValidationError as exc:
            logger.error("[%s] Merged JSON invalid: %s", label, exc)
            return model(**fallback), "fallback"

    try:
        return model(**data), "llm"
    except ValidationError as exc:
        logger.warning("[%s] Agent JSON validation failed: %s", label, exc)
        merged = {**fallback, **{k: v for k, v in data.items() if k in fallback}}
        try:
            return model(**merged), "merged"
        except ValidationError:
            logger.error("[%s] Merged agent JSON still invalid — full fallback", label)
            return model(**fallback), "fallback"


def validate_chief_verdict(
    raw: str,
    computed: dict[str, Any],
    *,
    label: str = "chief",
) -> tuple[ChiefVerdict, str]:
    """Validate chief narrative JSON; scores always from computed."""
    log_raw_output(label, raw)
    data = extract_json(raw, label=label)

    if data is None:
        logger.warning("[%s] Chief returned no JSON — using computed verdict only", label)
        return _computed_to_chief(computed), "computed"

    data["overall_score"] = computed["overall_score"]
    data["verdict"] = computed["verdict"]
    data["risk_level"] = computed.get("risk_level", data.get("risk_level", "MEDIUM"))
    data["agent_scores"] = computed["agent_scores"]
    for key in (
        "project_type", "submitted_project_type", "detected_project_type",
        "detected_project_confidence", "evaluation_standard", "scoring_weights", "score_band",
        "confidence", "confidence_explanation", "confidence_sources", "repository_statistics",
        "repository_completeness_score", "evidence_quality", "raw_weighted_score",
        "penalties", "calibration_adjustments", "missing_evidence", "positive_factors",
        "raw_agent_scores", "calibrated_agent_scores", "agent_calibration_reasons",
        "detected_technologies", "detected_algorithms", "architecture_summary",
        "evidence_found", "evidence_missing", "calibration_explanation",
        "project_type_justification", "community_impact_score",
    ):
        data[key] = computed.get(key)
    if computed.get("contradictions"):
        data.setdefault("contradictions", computed["contradictions"])
    if not data.get("executive_summary"):
        data["executive_summary"] = computed.get(
            "executive_summary",
            "Automated verdict synthesized from specialist jury scores.",
        )
    if not data.get("top_strengths"):
        data["top_strengths"] = computed.get("top_strengths", [])
    if not data.get("top_weaknesses"):
        data["top_weaknesses"] = computed.get("top_weaknesses", [])
    if not data.get("blocking_issues"):
        data["blocking_issues"] = computed.get("blocking_issues", [])
    if not data.get("deployment_roadmap"):
        data["deployment_roadmap"] = computed.get("deployment_roadmap") or computed.get("roadmap", [])
    if not data.get("roadmap"):
        data["roadmap"] = data.get("deployment_roadmap", [])
    if not data.get("recommended_fixes"):
        data["recommended_fixes"] = computed.get("recommended_fixes", [])

    try:
        return ChiefVerdict(**data), "llm"
    except ValidationError as exc:
        logger.warning("[%s] Chief verdict validation failed: %s — using computed", label, exc)
        return _computed_to_chief(computed), "computed"


def _computed_to_chief(computed: dict[str, Any]) -> ChiefVerdict:
    return ChiefVerdict(
        overall_score=computed["overall_score"],
        risk_level=computed.get("risk_level", "MEDIUM"),
        verdict=computed["verdict"],
        executive_summary=computed.get(
            "executive_summary",
            "Automated verdict from specialist jury scores.",
        ),
        top_strengths=computed.get("top_strengths", []),
        top_weaknesses=computed.get("top_weaknesses", []),
        contradictions=computed.get("contradictions", []),
        blocking_issues=computed.get("blocking_issues", []),
        recommended_fixes=computed.get("recommended_fixes", []),
        roadmap=computed.get("roadmap", computed.get("deployment_roadmap", [])),
        deployment_roadmap=computed.get("deployment_roadmap", computed.get("roadmap", [])),
        agent_scores=AgentScores(**computed["agent_scores"]),
        raw_agent_scores=AgentScores(**computed.get("raw_agent_scores", computed["agent_scores"])),
        calibrated_agent_scores=AgentScores(**computed.get("calibrated_agent_scores", computed["agent_scores"])),
        agent_calibration_reasons=computed.get("agent_calibration_reasons", {}),
        project_type=computed.get("project_type", "Hackathon Project"),
        submitted_project_type=computed.get("submitted_project_type", ""),
        detected_project_type=computed.get("detected_project_type", ""),
        detected_project_confidence=computed.get("detected_project_confidence", 0),
        evaluation_standard=computed.get("evaluation_standard", ""),
        scoring_weights=computed.get("scoring_weights", {}),
        score_band=computed.get("score_band", ""),
        confidence=computed.get("confidence", 0),
        confidence_explanation=computed.get("confidence_explanation", ""),
        confidence_sources=computed.get("confidence_sources", []),
        repository_statistics=computed.get("repository_statistics", {}),
        repository_completeness_score=computed.get("repository_completeness_score", 0),
        evidence_quality=computed.get("evidence_quality", ""),
        raw_weighted_score=computed.get("raw_weighted_score", 0),
        penalties=computed.get("penalties", []),
        calibration_adjustments=computed.get("calibration_adjustments", computed.get("penalties", [])),
        missing_evidence=computed.get("missing_evidence", []),
        positive_factors=computed.get("positive_factors", []),
        detected_technologies=computed.get("detected_technologies", []),
        detected_algorithms=computed.get("detected_algorithms", []),
        architecture_summary=computed.get("architecture_summary", ""),
        evidence_found=computed.get("evidence_found", []),
        evidence_missing=computed.get("evidence_missing", []),
        calibration_explanation=computed.get("calibration_explanation", ""),
        project_type_justification=computed.get("project_type_justification", ""),
        community_impact_score=computed.get("community_impact_score", 0),
    )
