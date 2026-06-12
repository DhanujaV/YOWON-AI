"""
Presenter: Integration/Tools team member
Purpose: Cover repository parsing, code intelligence helpers, and integration detection (GitHub, CI, infra).
This module provides helpers to extract integration signals and to build a small demo 'repo summary' output.
"""
from typing import Any


def integration_signals(code_summary: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    integrations = code_summary.get("integration_examples") or []
    repo_files = ctx.get("github", {}).get("repository_files") if isinstance(ctx.get("github"), dict) else []
    return {
        "integrations_detected": bool(integrations),
        "integration_examples": integrations[:6],
        "repo_files_count": len(repo_files or []),
    }

if __name__ == "__main__":
    print("integration_module loaded - call integration_signals(code_summary, ctx)")
