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

from dataclasses import asdict, dataclass
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from github import Github, GithubException
from security import validate_github_url
from config import (
    GITHUB_TOKEN,
    MAX_ANALYZED_SOURCE_FILES,
    MAX_GITHUB_FILE_BYTES,
    MAX_LINES_PER_FILE,
    MAX_REPOSITORY_FILES,
    MAX_TOTAL_CODE_CHARS,
    REPOSITORY_CACHE_DIR,
)

import logging
logger = logging.getLogger(__name__)

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".cs",
    ".php", ".rb", ".swift", ".kt", ".scala", ".sql", ".ipynb",
}
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".pdf", ".doc", ".docx"}
PRESENTATION_EXTENSIONS = {".ppt", ".pptx", ".key"}
DATA_EXTENSIONS = {".csv", ".tsv", ".jsonl", ".parquet", ".pkl", ".pickle", ".npy", ".npz", ".xlsx", ".xls", ".db", ".sqlite"}
CONFIG_FILENAMES = {
    "package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    "pom.xml", "build.gradle", "go.mod", "cargo.toml", "gemfile", "pipfile",
    "tsconfig.json", "vite.config.ts", "docker-compose.yml",
}
STAGE_ONE_FILENAMES = {
    "readme.md", "readme.rst", "readme.txt", "package.json", "requirements.txt",
    "requirements-dev.txt", "pyproject.toml", "dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "go.mod", "cargo.toml", "pom.xml", "build.gradle",
}
DEPLOYMENT_TERMS = (
    "dockerfile", "docker-compose.yml", "vercel.json", "netlify.toml", "render.yaml",
    "procfile", "kubernetes", "k8s", "helm", "terraform", ".github", "deploy",
)
IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "dist", "build",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".next", ".nuxt",
    "coverage", ".cache", "target", "out",
}
GENERATED_TERMS = (
    "generated", "bundle.js", "bundle.css", ".min.js", ".min.css",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
)
IMPORTANT_DIRS = (
    "api", "routes", "services", "models", "agents", "core", "backend", "frontend",
    "inference", "rag", "pipeline", "training", "auth", "database", "db", "server",
    "app", "src", "lib", "controllers", "schemas", "workers", "queues",
)
IMPORTANT_FILENAMES = (
    "main.py", "app.py", "server.py", "index.js", "index.ts", "api.py", "routes.py",
    "manage.py", "settings.py", "database.py", "models.py", "auth.py", "pipeline.py",
    "train.py", "inference.py", "dockerfile", "docker-compose.yml",
)
CACHE_TTL_SEC = 24 * 60 * 60


@dataclass(frozen=True)
class RepositoryMetrics:
    total_files: int = 0
    code_files: int = 0
    documentation_files: int = 0
    presentation_files: int = 0
    test_files: int = 0
    configuration_files: int = 0
    deployment_files: int = 0
    data_files: int = 0
    source_modules: int = 0
    meaningful_files: int = 0
    repository_completeness_score: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


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


def _limit_source_content(content: str) -> str:
    lines = content.splitlines()
    if len(lines) > MAX_LINES_PER_FILE:
        content = "\n".join(lines[:MAX_LINES_PER_FILE]) + "\n...[truncated source file]"
    return content


def _repo_name_from_url(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    safe_url = validate_github_url(url)
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", str(safe_url).rstrip("/"))
    if not match:
        raise ValueError(f"Cannot parse GitHub repo from URL: {url!r}")
    return match.group(1)


def _cache_path(repo_name: str) -> Path:
    digest = hashlib.sha256(repo_name.lower().encode("utf-8")).hexdigest()[:24]
    return REPOSITORY_CACHE_DIR / f"{digest}.json"


def _load_cached_repo(repo_name: str) -> dict[str, Any] | None:
    path = _cache_path(repo_name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if time.time() - float(payload.get("cached_at", 0)) > CACHE_TTL_SEC:
        return None
    data = payload.get("data")
    if isinstance(data, dict):
        data["cache"] = {"hit": True, "cached_at": payload.get("cached_at")}
        return data
    return None


def _store_cached_repo(repo_name: str, data: dict[str, Any]) -> None:
    payload = {"cached_at": time.time(), "repo": repo_name, "data": data}
    try:
        _cache_path(repo_name).write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass


def _suffix(path: str) -> str:
    name = path.lower().split("/")[-1]
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def _is_ignored_path(path: str) -> bool:
    p = path.replace("\\", "/").strip("/").lower()
    parts = p.split("/")
    if any(part in IGNORE_DIRS for part in parts):
        return True
    return any(term in p for term in GENERATED_TERMS)


def _importance_score(path: str) -> int:
    p = path.replace("\\", "/").strip("/").lower()
    name = p.split("/")[-1]
    parts = p.split("/")
    score = 0
    if name in IMPORTANT_FILENAMES:
        score += 80
    if _suffix(p) in SOURCE_EXTENSIONS:
        score += 35
    if any(part in IMPORTANT_DIRS for part in parts):
        score += 45
    if any(term in p for term in ("test", "spec", "__tests__")):
        score += 12
    if any(term in p for term in DEPLOYMENT_TERMS):
        score += 18
    if name in STAGE_ONE_FILENAMES:
        score += 20
    depth = max(0, len(parts) - 1)
    return score - min(20, depth * 3)


def _read_repo_file(repo, path: str) -> str:
    content_file = repo.get_contents(path)
    content = _safe_decode(content_file)
    if _suffix(path) in SOURCE_EXTENSIONS:
        content = _limit_source_content(content)
    return content


def _tree_file_paths(repo) -> list[str]:
    try:
        tree = repo.get_git_tree(repo.default_branch, recursive=True)
        paths = [
            item.path for item in tree.tree
            if getattr(item, "type", "") == "blob"
            and item.path
            and not _is_ignored_path(item.path)
        ]
        return paths[:MAX_REPOSITORY_FILES]
    except GithubException as exc:
        logger.warning("Recursive git tree failed: %s. Falling back to BFS manual dir crawl.", exc)
        paths = []
        queue = [""]
        visited_dirs = set()
        while queue and len(paths) < MAX_REPOSITORY_FILES:
            current_dir = queue.pop(0)
            try:
                contents = repo.get_contents(current_dir)
                if not isinstance(contents, list):
                    contents = [contents]
                for item in contents:
                    if item.type == "dir":
                        if item.path not in visited_dirs and not _is_ignored_path(item.path):
                            if item.path.count("/") < 4:
                                visited_dirs.add(item.path)
                                queue.append(item.path)
                    elif item.type == "file":
                        if not _is_ignored_path(item.path):
                            paths.append(item.path)
            except Exception as walk_exc:
                logger.warning("Failed listing contents of dir %s: %s", current_dir, walk_exc)
                continue
        return paths[:MAX_REPOSITORY_FILES]


def _folder_structure_from_paths(paths: list[str]) -> list[str]:
    entries: list[str] = []
    seen_dirs: set[str] = set()
    for path in paths:
        parts = path.split("/")
        for idx in range(1, len(parts)):
            directory = "/".join(parts[:idx])
            if directory not in seen_dirs:
                seen_dirs.add(directory)
                entries.append(f"{'  ' * (idx - 1)}[D] {directory}")
        entries.append(f"{'  ' * (len(parts) - 1)}[F] {path}")
    return entries[:MAX_REPOSITORY_FILES]


def _build_repository_statistics(file_paths: list[str]) -> RepositoryMetrics:
    lower = [path.lower() for path in file_paths if path and not _is_ignored_path(path)]
    code = [p for p in lower if _suffix(p) in SOURCE_EXTENSIONS]
    docs = [p for p in lower if _suffix(p) in DOC_EXTENSIONS or "readme" in p or "/docs/" in p]
    presentations = [p for p in lower if _suffix(p) in PRESENTATION_EXTENSIONS]
    tests = [p for p in lower if any(term in p for term in ("test", "spec", "__tests__"))]
    data = [p for p in lower if _suffix(p) in DATA_EXTENSIONS or "/data/" in p or p.startswith("data/")]
    configs = [
        p for p in lower
        if p.split("/")[-1] in CONFIG_FILENAMES
        or _suffix(p) in {".json", ".toml", ".yml", ".yaml", ".ini", ".cfg"}
    ]
    deployments = [p for p in lower if any(term in p for term in DEPLOYMENT_TERMS)]
    source_modules = {p.split("/")[0] for p in code if "/" in p} | {p.rsplit(".", 1)[0] for p in code}
    meaningful = set(code + docs + presentations + tests + configs + deployments + data)
    completeness = min(
        100,
        min(35, len(code) * 7)
        + min(15, len(docs) * 8)
        + min(15, len(tests) * 8)
        + min(10, len(configs) * 4)
        + min(10, len(deployments) * 10)
        + min(8, len(data) * 4)
        + min(15, len(source_modules) * 4),
    )
    return RepositoryMetrics(
        total_files=len(lower),
        code_files=len(code),
        documentation_files=len(docs),
        presentation_files=len(presentations),
        test_files=len(tests),
        configuration_files=len(configs),
        deployment_files=len(deployments),
        data_files=len(data),
        source_modules=len(source_modules),
        meaningful_files=len(meaningful),
        repository_completeness_score=completeness,
    )


def extract_github_data(github_url: str) -> dict[str, Any]:
    """
    Main entry point.  Returns a structured dict with all extracted info.
    """
    from utils.git_provider import GitHubProvider
    provider = GitHubProvider()

    repo_name = _repo_name_from_url(github_url)
    cached = _load_cached_repo(repo_name)
    if cached and "commit_sha" in cached:
        return cached

    try:
        details = provider.get_repo_details(github_url)
        commit_details = provider.get_latest_commit(github_url)
    except Exception as exc:
        return {"error": f"Git provider error: {str(exc)}"}

    gh = _github_client()
    try:
        repo = gh.get_repo(repo_name)
    except GithubException as exc:
        if exc.status == 401 or "bad credentials" in str(exc).lower():
            logger.warning("[GitHub] Client token failed (Bad credentials). Falling back to anonymous client.")
            gh = Github()
            try:
                repo = gh.get_repo(repo_name)
            except GithubException as inner_exc:
                return {"error": f"GitHub API error: {inner_exc.data.get('message', str(inner_exc))}"}
        else:
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
        "repository_files": [],
        "repository_statistics": {},
        "dependencies": {},
        "python_files": [],
        "source_files": [],
        "analyzed_source_files": [],
        "top_code_snippets": [],
        "cache": {"hit": False},
        "github_repository_id": details.get("github_repository_id"),
        "owner": details.get("owner"),
        "repository_name": details.get("repository_name"),
        "default_branch": details.get("default_branch"),
        "visibility": details.get("visibility"),
        "license": details.get("license"),
        "commit_sha": commit_details.get("commit_sha"),
        "tree_sha": commit_details.get("tree_sha"),
        "branch": commit_details.get("branch"),
        "last_commit_timestamp": commit_details.get("last_commit_timestamp").isoformat() if commit_details.get("last_commit_timestamp") else None,
    }

    # ── README ──────────────────────────────────────────────────────────────
    try:
        readme = repo.get_readme()
        result["readme"] = _safe_decode(readme)[:6000]
    except GithubException:
        result["readme"] = "[No README found]"

    # Stage 2: repository map from the Git tree. This is much faster than
    # walking directories with one API call per folder on large repositories.
    file_paths = _tree_file_paths(repo)
    if not file_paths:
        try:
            root_contents = repo.get_contents("")
            file_paths = [
                item.path for item in root_contents
                if getattr(item, "type", "") == "file" and not _is_ignored_path(item.path)
            ][:MAX_REPOSITORY_FILES]
        except GithubException:
            file_paths = []
    result["folder_structure"] = _folder_structure_from_paths(file_paths)
    result["repository_files"] = file_paths
    result["repository_statistics"] = _build_repository_statistics(file_paths).as_dict()

    # ── Dependency files ──────────────────────────────────────────────────────
    stage_one_paths = [
        path for path in file_paths
        if path.lower().split("/")[-1] in STAGE_ONE_FILENAMES
        or path.lower().startswith(".github/workflows/")
    ]
    dep_files = sorted(set(stage_one_paths), key=lambda p: ("/" in p, p.lower()))
    for fname in dep_files[:25]:
        try:
            result["dependencies"][fname] = _read_repo_file(repo, fname)
        except GithubException:
            pass

    # Stage 3: ranked source sampling. Reads only high-signal files and enforces
    # repository, file, and total-code budgets for predictable evaluation time.
    source_paths = [
        path for path in file_paths
        if _suffix(path) in SOURCE_EXTENSIONS and not _is_ignored_path(path)
    ]
    ranked_source_paths = sorted(
        source_paths,
        key=lambda path: (-_importance_score(path), path.count("/"), path.lower()),
    )[:MAX_ANALYZED_SOURCE_FILES]

    py_files: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    total_chars = 0
    for path in ranked_source_paths:
        if total_chars >= MAX_TOTAL_CODE_CHARS:
            break
        try:
            content = _read_repo_file(repo, path)
        except GithubException:
            continue
        remaining = max(0, MAX_TOTAL_CODE_CHARS - total_chars)
        if len(content) > remaining:
            content = content[:remaining] + "\n...[truncated total code budget]"
        sample = {
            "path": path,
            "content": content,
            "importance_score": _importance_score(path),
        }
        source_files.append(sample)
        total_chars += len(content)
        if path.lower().endswith(".py") and len(py_files) < MAX_ANALYZED_SOURCE_FILES:
            py_files.append(sample)

    result["python_files"] = py_files
    result["source_files"] = source_files
    result["analyzed_source_files"] = [
        {"path": item["path"], "importance_score": item["importance_score"]}
        for item in source_files
    ]
    result["top_code_snippets"] = [
        {
            "path": item["path"],
            "snippet": "\n".join(str(item["content"]).splitlines()[:40]),
        }
        for item in source_files[:8]
    ]

    try:
        result["contributors"] = repo.get_contributors().totalCount
    except Exception:
        result["contributors"] = 0
    try:
        result["releases"] = repo.get_releases().totalCount
    except Exception:
        result["releases"] = 0
    try:
        result["open_issues"] = repo.open_issues_count
    except Exception:
        result["open_issues"] = 0

    _store_cached_repo(repo_name, result)
    return result
