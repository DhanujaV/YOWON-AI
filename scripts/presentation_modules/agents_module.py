"""
Presenter: Agents/LLM team member
Purpose: Explain how agent systems, CrewAI and LLM integrations are detected and summarized.
This module provides helpers that extract agent-related signals and generate an example agent task for demonstration.
"""
from typing import Any
import json


def agent_signals(code_summary: dict[str, Any]) -> dict[str, Any]:
    signals = code_summary.get("signals") or {}
    return {
        "agent_system": signals.get("agent_system"),
        "vector_db": signals.get("vector_database"),
    }


def example_agent_task(numeric_summary: dict[str, Any]) -> str:
    """Build a compact example agent task prompt for the demo."""
    task = {
        "instruction": "Given these numeric results, produce a short executive summary.",
        "numeric_summary": numeric_summary,
        "return": ["executive_summary", "key_findings"]
    }
    return json.dumps(task, indent=2)

if __name__ == "__main__":
    print("agents_module loaded - call agent_signals(code_summary) or example_agent_task(summary)")
