"""
Presenter: Backend team member
Purpose: Explain how backend/API/database signals are detected and scored.
This module hosts helpers that mirror `read_codebase` / `summarize_architecture`'s backend parts for demonstration.
"""
from typing import Any


def backend_signals(code_summary: dict[str, Any]) -> dict[str, Any]:
    """Return backend-related signals and short examples."""
    signals = code_summary.get("signals") or {}
    api_examples = code_summary.get("api_examples") or []
    db_examples = code_summary.get("database_examples") or []
    return {
        "rest_api": signals.get("rest_api"),
        "database": signals.get("database"),
        "api_examples": api_examples[:6],
        "database_examples": db_examples[:6],
    }

if __name__ == "__main__":
    print("backend_module loaded - call backend_signals(code_summary)")
