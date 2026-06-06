"""In-memory evaluation progress for SSE and polling — real-time agent tracking."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Literal

_lock = threading.Lock()
TOTAL_STEPS = 8

AGENT_ORDER = [
    "coordinator",
    "technical",
    "security",
    "presentation",
    "innovation",
    "risk",
    "scoring",
    "chief",
]

AGENT_LABELS = {
    "coordinator": "Coordinator",
    "brief": "Coordinator",
    "technical": "Technical Review",
    "engineering": "Technical Review",
    "security": "Security Audit",
    "presentation": "Presentation Review",
    "innovation": "Innovation Analysis",
    "risk": "Risk Assessment",
    "scoring": "Score Engine",
    "chief": "Chief Verdict",
    "initializing": "Initializing",
    "done": "Complete",
}

AGENT_TASKS = {
    "coordinator": "Building evaluation context",
    "brief": "Building evaluation context",
    "technical": "Technical review — architecture and code quality",
    "engineering": "Technical review — architecture and code quality",
    "security": "Security audit — OWASP and static scan findings",
    "presentation": "Presentation review — pitch and documentation",
    "innovation": "Innovation analysis — novelty and scalability",
    "risk": "Risk assessment — impact and failure modes",
    "scoring": "Computing weighted scores and contradictions",
    "chief": "Chief verdict — cross-exam and synthesis",
}

# Pre-pipeline phases (coordinator step)
PHASE_FETCH_REPO = "Fetching repository"
PHASE_BUILD_CONTEXT = "Building context"
PHASE_EMBEDDINGS = "Generating embeddings"
PHASE_REPORT = "Report generation"

AGENT_STEPS = {
    "coordinator": 0,
    "brief": 0,
    "technical": 1,
    "engineering": 1,
    "security": 2,
    "presentation": 3,
    "innovation": 4,
    "risk": 5,
    "scoring": 6,
    "chief": 7,
}

AgentPhase = Literal["waiting", "running", "completed", "failed"]

_progress: dict[str, dict[str, Any]] = defaultdict(dict)


def _empty_agent_state() -> dict[str, Any]:
    return {
        "status": "waiting",
        "started_at": None,
        "ended_at": None,
        "duration_sec": None,
        "model": None,
        "error": None,
    }


def _default_state() -> dict[str, Any]:
    return {
        "step": 0,
        "total": TOTAL_STEPS,
        "agent": "coordinator",
        "current_task": PHASE_BUILD_CONTEXT,
        "status": "running",
        "evaluation_status": "running",
        "report_status": "pending",
        "report_error": None,
        "started_at": time.time(),
        "elapsed_seconds": 0,
        "completion_percent": 0,
        "logs": [],
        "agent_states": {name: _empty_agent_state() for name in AGENT_ORDER},
        "events": [],
    }


def _compute_completion(agent_states: dict[str, Any]) -> int:
    completed = sum(
        1 for name in AGENT_ORDER if agent_states.get(name, {}).get("status") == "completed"
    )
    running = any(
        agent_states.get(name, {}).get("status") == "running" for name in AGENT_ORDER
    )
    pct = int((completed / TOTAL_STEPS) * 100)
    if running and pct < 99:
        pct = min(99, pct + 5)
    return pct


def init_progress(project_id: str, *, reset: bool = False) -> None:
    with _lock:
        existing = _progress.get(project_id)
        if existing and not reset:
            return
        _progress[project_id] = _default_state()
        state = _progress[project_id]
        state.setdefault("logs", []).append("[SYS] Evaluation pipeline initialized")


def set_current_task(
    project_id: str,
    task: str,
    *,
    log: str | None = None,
    agent: str = "coordinator",
) -> None:
    """Update UI task label during pre-agent phases (fetch, embed, etc.)."""
    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        state["current_task"] = task
        state["agent"] = agent
        state["elapsed_seconds"] = round(time.time() - state.get("started_at", time.time()))
        if log:
            logs: list[str] = state.setdefault("logs", [])
            logs.append(log)
            state["logs"] = logs[-80:]


def agent_start(
    project_id: str,
    agent: str,
    *,
    model: str = "",
    message: str | None = None,
) -> None:
    agent_key = "coordinator" if agent in ("brief", "coordinator") else agent
    step = AGENT_STEPS.get(agent_key, AGENT_STEPS.get(agent, 0))
    label = AGENT_LABELS.get(agent_key, agent_key)
    task = AGENT_TASKS.get(agent_key, f"Running {label}")

    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        state["step"] = step
        state["agent"] = agent_key
        state["current_task"] = task
        state["status"] = "running"
        state["elapsed_seconds"] = round(time.time() - state.get("started_at", time.time()))

        agent_states = state.setdefault("agent_states", {n: _empty_agent_state() for n in AGENT_ORDER})
        agent_states[agent_key] = {
            "status": "running",
            "started_at": time.time(),
            "ended_at": None,
            "duration_sec": None,
            "model": model or None,
            "error": None,
        }
        state["completion_percent"] = _compute_completion(agent_states)

        log_msg = message or f"[{label.upper()}] Started"
        if model:
            log_msg += f" (model={model})"
        logs: list[str] = state.setdefault("logs", [])
        logs.append(log_msg)
        state["logs"] = logs[-80:]

        events: list[dict] = state.setdefault("events", [])
        events.append({
            "type": "agent_start",
            "agent": agent_key,
            "step": step,
            "model": model,
            "ts": time.time(),
        })
        state["events"] = events[-40:]


def agent_complete(
    project_id: str,
    agent: str,
    *,
    message: str | None = None,
    duration_sec: float | None = None,
    error: str | None = None,
) -> None:
    agent_key = "coordinator" if agent in ("brief", "coordinator") else agent
    label = AGENT_LABELS.get(agent_key, agent_key)

    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        agent_states = state.setdefault("agent_states", {n: _empty_agent_state() for n in AGENT_ORDER})
        entry = agent_states.setdefault(agent_key, _empty_agent_state())

        now = time.time()
        started = entry.get("started_at") or state.get("started_at", now)
        elapsed = duration_sec if duration_sec is not None else round(now - started, 2)

        entry["status"] = "failed" if error else "completed"
        entry["ended_at"] = now
        entry["duration_sec"] = elapsed
        if error:
            entry["error"] = error

        state["elapsed_seconds"] = round(now - state.get("started_at", now))
        state["completion_percent"] = _compute_completion(agent_states)

        if error:
            log_msg = message or f"[{label.upper()}] Failed after {elapsed}s — {error}"
        else:
            log_msg = message or f"[{label.upper()}] Completed in {elapsed}s"
        logs: list[str] = state.setdefault("logs", [])
        logs.append(log_msg)
        state["logs"] = logs[-80:]

        events: list[dict] = state.setdefault("events", [])
        events.append({
            "type": "agent_complete",
            "agent": agent_key,
            "duration_sec": elapsed,
            "error": error,
            "ts": now,
        })
        state["events"] = events[-40:]


def emit(
    project_id: str,
    *,
    step: int,
    agent: str,
    message: str,
    status: str = "running",
    current_task: str | None = None,
) -> None:
    agent_key = "coordinator" if agent in ("brief", "coordinator") else agent
    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        state["step"] = step
        state["agent"] = agent_key
        state["status"] = status
        if current_task:
            state["current_task"] = current_task
        else:
            state["current_task"] = AGENT_TASKS.get(agent_key, message)
        state["elapsed_seconds"] = round(time.time() - state.get("started_at", time.time()))
        logs: list[str] = state.setdefault("logs", [])
        logs.append(message)
        state["logs"] = logs[-80:]


def complete(
    project_id: str,
    *,
    report_status: str = "ready",
    report_error: str | None = None,
) -> None:
    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        state["step"] = TOTAL_STEPS
        state["agent"] = "done"
        state["current_task"] = (
            PHASE_REPORT + " — failed" if report_status == "failed" else "Evaluation complete"
        )
        state["status"] = "done"
        state["evaluation_status"] = "complete"
        state["report_status"] = report_status
        state["report_error"] = report_error
        state["completion_percent"] = 100
        state["elapsed_seconds"] = round(time.time() - state.get("started_at", time.time()))
        if report_status == "failed":
            state.setdefault("logs", []).append(
                f"[SYS] Evaluation complete — {PHASE_REPORT} failed: {report_error or 'unknown'}"
            )
        else:
            state.setdefault("logs", []).append("[SYS] Evaluation complete — verdict ready")


def fail(project_id: str, message: str) -> None:
    with _lock:
        state = _progress.setdefault(project_id, _default_state())
        state["status"] = "failed"
        state["evaluation_status"] = "failed"
        state["report_status"] = "skipped"
        state["report_error"] = message
        state["current_task"] = "Evaluation failed"
        state["elapsed_seconds"] = round(time.time() - state.get("started_at", time.time()))
        state.setdefault("logs", []).append(f"[ERR] {message}")


def get_progress(project_id: str) -> dict[str, Any]:
    with _lock:
        state = _progress.get(project_id)
        if not state:
            return {"status": "unknown", "step": 0, "total": TOTAL_STEPS}
        out = dict(state)
        if out.get("started_at"):
            out["elapsed_seconds"] = round(time.time() - out["started_at"])
        return out


def clear_progress(project_id: str) -> None:
    with _lock:
        _progress.pop(project_id, None)
