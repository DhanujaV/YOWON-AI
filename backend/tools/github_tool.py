"""
tools/github_tool.py — GitHub repository data extractor.

Uses PyGithub to pull:
  - README content
  - Repository metadata (stars, forks, topics, language breakdown)
  - Top-level folder structure (2 levels deep)
  - Dependency files (requirements.txt, package.json, pom.xml, etc.)
  - A sample of Python source files for static analysis
"""

from __future__ import annotations

import re
from typing import Any

from github import Github, GithubException
from config import GITHUB_TOKEN, MAX_GITHUB_FILE_BYTES


def _github_client() -> Github:
    """Return an authenticated (or anonymous) PyGithub client."""
    return Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()


def _safe_decode(content_file) -> str:
    """Decode a GitHub ContentFile safely, respecting the size limit."""
    if content_file.size > MAX_GITHUB_FILE_BYTES:
        return f"[File too large to display: {content_file.size} bytes]"
    try:
        return content_file.decoded_content.decode("utf-8", errors="replace")
    except Exception as exc:
        return f"[Could not decode file: {exc}]"


def _repo_name_from_url(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url.rstrip("/"))
    if not match:
        raise ValueError(f"Cannot parse GitHub repo from URL: {url!r}")
    return match.group(1)


def extract_github_data(github_url: str) -> dict[str, Any]:
    """
    Main entry point.  Returns a structured dict with all extracted info.

    Keys:
      name, description, url, stars, forks, language, topics,
      readme, folder_structure, dependencies, python_files
    """
    gh = _github_client()
    repo_name = _repo_name_from_url(github_url)

    try:
        repo = gh.get_repo(repo_name)
    except GithubException as exc:
        return {"error": f"GitHub API error: {exc.data.get('message', str(exc))}"}

    result: dict[str, Any] = {
        "name": repo.full_name,
        "description": repo.description or "",
        "url": repo.html_url,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "language": repo.language or "Unknown",
        "topics": repo.get_topics(),
        "readme": "",
        "folder_structure": [],
        "dependencies": {},
        "python_files": [],
    }

    # ── README ──────────────────────────────────────────────────────────────
    try:
        readme = repo.get_readme()
        result["readme"] = _safe_decode(readme)[:6000]
    except GithubException:
        result["readme"] = "[No README found]"

    # ── Folder structure (2 levels) ──────────────────────────────────────────
    try:
        root_contents = repo.get_contents("")
        structure: list[str] = []
        queue = list(root_contents)
        depth_map: dict[str, int] = {item.path: 1 for item in root_contents}

        while queue:
            item = queue.pop(0)
            depth = depth_map.get(item.path, 1)
            prefix = "  " * (depth - 1)
            icon = "📁" if item.type == "dir" else "📄"
            structure.append(f"{prefix}{icon} {item.name}")

            if item.type == "dir" and depth < 2:
                try:
                    children = repo.get_contents(item.path)
                    for child in children:
                        depth_map[child.path] = depth + 1
                    queue.extend(children)
                except GithubException:
                    pass

        result["folder_structure"] = structure[:200]  # Cap at 200 entries
    except GithubException:
        pass

    # ── Dependency files ──────────────────────────────────────────────────────
    dep_files = [
        "requirements.txt", "requirements-dev.txt",
        "package.json", "package-lock.json",
        "pom.xml", "build.gradle",
        "Pipfile", "pyproject.toml",
        "Gemfile", "go.mod",
    ]
    for fname in dep_files:
        try:
            content_file = repo.get_contents(fname)
            result["dependencies"][fname] = _safe_decode(content_file)
        except GithubException:
            pass

    # ── Python source files (up to 5 files for static analysis) ──────────────
    try:
        py_files: list[dict] = []
        contents = repo.get_contents("")
        queue = list(contents)
        while queue and len(py_files) < 5:
            item = queue.pop(0)
            if item.type == "file" and item.name.endswith(".py"):
                py_files.append({
                    "path": item.path,
                    "content": _safe_decode(item),
                })
            elif item.type == "dir":
                try:
                    queue.extend(repo.get_contents(item.path))
                except GithubException:
                    pass
        result["python_files"] = py_files
    except GithubException:
        pass

    return result