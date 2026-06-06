"""
tools/security_tool.py — Static security analysis for Project Sentinel.

Combines:
  1. Bandit — SAST tool for Python code
  2. Regex-based secret detection (hardcoded API keys, passwords, tokens)
  3. Dependency vulnerability notes (heuristic, no network call)
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


# ── Secret patterns ──────────────────────────────────────────────────────────
SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)api[_\s-]?key\s*[:=]\s*['\"][\w\-]{16,}['\"]", "Hardcoded API key"),
    (r"(?i)secret[_\s-]?key\s*[:=]\s*['\"][\w\-]{16,}['\"]", "Hardcoded secret key"),
    (r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}['\"]", "Hardcoded password"),
    (r"(?i)token\s*[:=]\s*['\"][\w\-]{20,}['\"]", "Hardcoded token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)private[_\s]?key\s*[:=]", "Private key reference"),
    (r"mongodb(\+srv)?://[^\"'\s]+", "MongoDB connection string with credentials"),
    (r"postgres://[^\"'\s]+:[^\"'\s]+@", "PostgreSQL connection string with credentials"),
]


def _detect_secrets(code: str, filename: str = "unknown") -> list[dict]:
    """Scan code string for common secret patterns."""
    findings: list[dict] = []
    for line_num, line in enumerate(code.splitlines(), start=1):
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append({
                    "file": filename,
                    "line": line_num,
                    "issue": label,
                    "severity": "HIGH",
                    "snippet": line.strip()[:120],
                })
    return findings


def _run_bandit(python_files: list[dict]) -> list[dict]:
    """
    Write Python files to a temp directory and run Bandit.
    Returns list of Bandit issue dicts.
    """
    if not python_files:
        return []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Write files
        for f in python_files:
            safe_name = f["path"].replace("/", "__")
            (tmp_path / safe_name).write_text(f["content"], encoding="utf-8")

        try:
            result = subprocess.run(
                ["bandit", "-r", str(tmp_path), "-f", "json", "-q"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            raw = result.stdout or result.stderr
            data = json.loads(raw) if raw.strip().startswith("{") else {}
            issues = data.get("results", [])
            return [
                {
                    "file": issue.get("filename", ""),
                    "line": issue.get("line_number", 0),
                    "issue": issue.get("issue_text", ""),
                    "severity": issue.get("issue_severity", ""),
                    "confidence": issue.get("issue_confidence", ""),
                    "test_id": issue.get("test_id", ""),
                }
                for issue in issues
            ]
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []


def _check_dependencies(dep_files: dict[str, str]) -> list[dict]:
    """
    Heuristic dependency checks — flags known-risky patterns without network.
    Real production systems would integrate with safety or osv-scanner.
    """
    warnings: list[dict] = []

    # Look for unpinned dependencies in requirements.txt
    req_content = dep_files.get("requirements.txt", "")
    for line in req_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "==" not in line and ">=" not in line:
            warnings.append({
                "file": "requirements.txt",
                "issue": f"Unpinned dependency: {line!r}",
                "severity": "LOW",
            })

    return warnings


def run_security_analysis(
    python_files: list[dict],
    dep_files: dict[str, str],
) -> dict[str, Any]:
    """
    Run full security analysis and return consolidated findings.

    Args:
        python_files: list of {"path": str, "content": str}
        dep_files:    dict of filename → file content

    Returns:
        {
          "bandit_issues": list,
          "secret_findings": list,
          "dependency_warnings": list,
          "summary": str,
          "risk_level": str,   # LOW | MEDIUM | HIGH | CRITICAL
        }
    """
    bandit_issues = _run_bandit(python_files)

    secret_findings: list[dict] = []
    for f in python_files:
        secret_findings.extend(_detect_secrets(f["content"], f["path"]))

    dep_warnings = _check_dependencies(dep_files)

    # ── Compute overall risk level ────────────────────────────────────────
    critical_count = sum(1 for i in bandit_issues if i.get("severity") == "HIGH")
    critical_count += len(secret_findings)

    if critical_count >= 5:
        risk = "CRITICAL"
    elif critical_count >= 2:
        risk = "HIGH"
    elif len(bandit_issues) >= 3:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    summary = (
        f"Bandit found {len(bandit_issues)} issue(s). "
        f"{len(secret_findings)} potential secret(s) detected. "
        f"{len(dep_warnings)} dependency warning(s)."
    )

    return {
        "bandit_issues": bandit_issues,
        "secret_findings": secret_findings,
        "dependency_warnings": dep_warnings,
        "summary": summary,
        "risk_level": risk,
    }