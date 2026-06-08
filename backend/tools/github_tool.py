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
import re
from typing import Any

from github import Github, GithubException
from config import GITHUB_TOKEN, MAX_GITHUB_FILE_BYTES

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


def _repo_name_from_url(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url.rstrip("/"))
    if not match:
        raise ValueError(f"Cannot parse GitHub repo from URL: {url!r}")
    return match.group(1)


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
        "repository_files": [],
        "repository_statistics": {},
        "dependencies": {},
        "python_files": [],
        "source_files": [],
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
        file_paths: list[str] = []
        queue = list(root_contents)
        depth_map: dict[str, int] = {item.path: 1 for item in root_contents}

        while queue:
            item = queue.pop(0)
            depth = depth_map.get(item.path, 1)
            if _is_ignored_path(item.path):
                continue
            prefix = "  " * (depth - 1)
            icon = "📁" if item.type == "dir" else "📄"
            structure.append(f"{prefix}{icon} {item.path}")
            if item.type == "file":
                file_paths.append(item.path)

            if item.type == "dir":
                try:
                    children = repo.get_contents(item.path)
                    for child in children:
                        depth_map[child.path] = depth + 1
                    queue.extend(children)
                except GithubException:
                    pass

        result["folder_structure"] = structure[:200]  # Cap at 200 entries
        result["repository_files"] = file_paths[:1000]
        result["repository_statistics"] = _build_repository_statistics(file_paths).as_dict()
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
        source_files: list[dict] = []
        contents = repo.get_contents("")
        queue = list(contents)
        while queue and len(source_files) < 20:
            item = queue.pop(0)
            if _is_ignored_path(item.path):
                continue
            if item.type == "file" and _suffix(item.path) in SOURCE_EXTENSIONS:
                sample = {
                    "path": item.path,
                    "content": _safe_decode(item),
                }
                source_files.append(sample)
                if item.name.endswith(".py") and len(py_files) < 8:
                    py_files.append(sample)
            elif item.type == "dir":
                try:
                    queue.extend(repo.get_contents(item.path))
                except GithubException:
                    pass
        result["python_files"] = py_files
        result["source_files"] = source_files
    except GithubException:
        pass

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

    return result
