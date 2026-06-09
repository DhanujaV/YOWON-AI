"""Historical percentile ranking for completed YOWON AI evaluations.

This module is intentionally independent from scoring, calibration, LLMs,
repository analysis, and PDF generation. It stores only evaluation metadata.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_FILE = Path(__file__).resolve().parents[1] / "data" / "evaluation_history.json"
MIN_HISTORY_SIZE = 25
INSUFFICIENT_RANK = "Insufficient Data"


def _ensure_history_file() -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")


def _valid_entry(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    try:
        score = int(float(item.get("overall_score")))
    except Exception:
        return None
    project_name = str(item.get("project_name") or "Unknown Project")
    project_type = str(item.get("project_type") or "Hackathon Project")
    timestamp = str(item.get("timestamp") or "")
    return {
        "project_name": project_name,
        "project_type": project_type,
        "overall_score": max(0, min(100, score)),
        "timestamp": timestamp,
    }


def load_history() -> list[dict[str, Any]]:
    """Load historical evaluation metadata from disk."""
    _ensure_history_file()
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [entry for item in raw if (entry := _valid_entry(item)) is not None]


def _write_history(history: list[dict[str, Any]]) -> None:
    _ensure_history_file()
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def save_evaluation(
    project_name: str,
    project_type: str,
    overall_score: int | float,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Append one completed evaluation metadata record and return the record."""
    history = load_history()
    record = {
        "project_name": str(project_name or "Unknown Project"),
        "project_type": str(project_type or "Hackathon Project"),
        "overall_score": max(0, min(100, int(round(float(overall_score))))),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
    history.append(record)
    _write_history(history)
    return record


def _percentile(score: int | float, entries: list[dict[str, Any]]) -> int | None:
    if len(entries) < MIN_HISTORY_SIZE:
        return None
    bounded_score = max(0, min(100, float(score)))
    lower_count = sum(1 for item in entries if float(item.get("overall_score", 0)) < bounded_score)
    return round(lower_count / len(entries) * 100)


def _rank_label(percentile: int | None) -> str:
    if percentile is None:
        return INSUFFICIENT_RANK
    return f"Top {max(0, 100 - percentile)}%"


def calculate_global_percentile(score: int | float) -> int | None:
    """Return percentile among all historical projects, or None if insufficient."""
    return _percentile(score, load_history())


def calculate_category_percentile(score: int | float, project_type: str) -> int | None:
    """Return percentile among projects of the same type, or None if insufficient."""
    history = [
        item for item in load_history()
        if str(item.get("project_type") or "") == str(project_type or "")
    ]
    return _percentile(score, history)


def calculate_global_rank(score: int | float) -> str:
    """Return display rank among all projects."""
    return _rank_label(calculate_global_percentile(score))


def calculate_category_rank(score: int | float, project_type: str) -> str:
    """Return display rank among projects of the same type."""
    return _rank_label(calculate_category_percentile(score, project_type))


def build_ranking_payload(score: int | float, project_type: str) -> dict[str, Any]:
    """Build the API ranking payload from persisted history."""
    history = load_history()
    category_history = [
        item for item in history
        if str(item.get("project_type") or "") == str(project_type or "")
    ]
    global_percentile = _percentile(score, history)
    category_percentile = _percentile(score, category_history)
    return {
        "global_percentile": global_percentile,
        "global_rank": _rank_label(global_percentile),
        "category_percentile": category_percentile,
        "category_rank": _rank_label(category_percentile),
        "projects_compared": len(history),
        "category_projects_compared": len(category_history),
    }
