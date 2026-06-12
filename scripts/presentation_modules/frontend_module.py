"""
Presenter: Frontend team member
Purpose: Explain how the frontend layer is detected and summarized.
This module extracts frontend-related signals from the code intelligence summary and provides simple helper functions used during the presentation.
"""
from typing import Any


def frontend_signals(code_summary: dict[str, Any], architecture: dict[str, Any]) -> dict[str, Any]:
    """Return frontend-related findings and examples."""
    frameworks = code_summary.get("frameworks") or []
    files = code_summary.get("sampled_files") or []
    present = architecture.get("layers", {}).get("frontend", False)
    return {
        "frontend_detected": bool(present),
        "frameworks": frameworks,
        "sample_files": files[:8],
    }


if __name__ == "__main__":
    print("frontend_module loaded - call frontend_signals(code_summary, architecture)")
