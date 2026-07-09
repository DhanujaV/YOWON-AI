"""
repository_scan.py — Single normalized source of truth for repository file data.

All [F] / [D] prefix stripping happens ONCE here.
Every other module reads from RepositoryScan — no raw string manipulation elsewhere.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class RepositoryScan:
    """
    Normalized, immutable view of repository data loaded from DB snapshot + GitHub cache.

    Created ONCE at the start of intelligence_service.run_repository_intelligence().
    All downstream engines consume this object — there are no additional file reads.
    """
    snapshot_id: str
    commit_sha: str
    github_url: str

    # Normalized file paths — no [F]/[D] prefixes, forward slashes only
    files: List[str] = field(default_factory=list)

    # Source file contents: path → source text
    file_contents: Dict[str, str] = field(default_factory=dict)

    # Raw dependency text: manifest filename → raw content
    dependency_manifests: Dict[str, str] = field(default_factory=dict)

    # Parsed dependency map: dep name → version string
    raw_dependencies: Dict[str, str] = field(default_factory=dict)

    # Original folder_structure entries (kept for debugging)
    folder_structure_raw: List[str] = field(default_factory=list)

    # Repository name (display)
    repository_name: str = "Unknown Repository"

    @staticmethod
    def normalize_path(entry: str) -> str:
        """
        Strip [F], [D] display prefixes and indentation from a folder_structure entry.
        Returns a clean forward-slash path string.
        """
        s = entry.strip()
        # Strip bracketed type markers used by GitHub tool for display
        for prefix in ("[F] ", "[D] ", "[F]", "[D]"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        return s.replace("\\", "/").strip()

    @classmethod
    def from_snapshot(cls, snapshot: Any, db: Any) -> "RepositoryScan":
        """
        Build a normalized RepositoryScan from a DB RepositorySnapshot record.
        Loads file contents from the GitHub tool disk cache.
        """
        snapshot_id = str(snapshot.snapshot_id)
        commit_sha = str(snapshot.commit_sha or "")
        github_url = ""
        repository_name = "Unknown Repository"

        try:
            if snapshot.repository:
                github_url = str(snapshot.repository.github_url or "")
                # Resolve display name
                for attr in ("repository_name", "repo_name", "display_name", "project_name", "title"):
                    val = getattr(snapshot.repository, attr, None)
                    if val and str(val).strip():
                        repository_name = str(val).strip()
                        break
        except Exception:
            pass

        # ── 1. Parse folder_structure → normalized file list ──────────────────
        files: List[str] = []
        folder_structure_raw: List[str] = []
        if snapshot.folder_structure:
            try:
                raw_entries = json.loads(snapshot.folder_structure)
                if isinstance(raw_entries, list):
                    folder_structure_raw = raw_entries
                    for entry in raw_entries:
                        s = str(entry).strip()
                        # Determine if this is a file [F] or directory [D] entry
                        is_file = False
                        is_dir = False
                        for prefix in ("[F] ", "[F]"):
                            if s.startswith(prefix):
                                is_file = True
                                break
                        if not is_file:
                            for prefix in ("[D] ", "[D]"):
                                if s.startswith(prefix):
                                    is_dir = True
                                    break
                        if not is_file and not is_dir:
                            # No marker — use heuristic: has a dot extension = file
                            basename = s.split("/")[-1]
                            is_file = "." in basename

                        # Only include files, not directories
                        if is_file:
                            clean = cls.normalize_path(s)
                            if clean:
                                files.append(clean)
            except Exception as e:
                logger.warning("[RepositoryScan] Failed to parse folder_structure: %s", e)

        # ── DIAGNOSTIC: Log tree build inputs ────────────────────────────────
        logger.info(
            "[RepositoryScan][DIAG] folder_structure parsed: total_entries=%d file_entries=%d",
            len(folder_structure_raw), len(files)
        )
        if files:
            logger.info(
                "[RepositoryScan][DIAG] First 5 file paths: %s",
                files[:5]
            )

        # ── 2. Parse dependency_summary → raw_dependencies dict ───────────────
        raw_dependencies: Dict[str, str] = {}
        if snapshot.dependency_summary:
            try:
                parsed = json.loads(snapshot.dependency_summary)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        raw_dependencies[str(k)] = str(v) if v is not None else ""
                elif isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("package", "")
                            version = item.get("version", "")
                            if name:
                                raw_dependencies[str(name)] = str(version)
                        elif isinstance(item, str):
                            raw_dependencies[item] = ""
            except Exception as e:
                logger.warning("[RepositoryScan] Failed to parse dependency_summary: %s", e)

        # ── 3. Load file contents from GitHub tool disk cache ─────────────────
        file_contents: Dict[str, str] = {}
        dependency_manifests: Dict[str, str] = {}
        if github_url:
            file_contents, dependency_manifests = cls._load_github_cache(github_url, files)

        logger.info(
            "[RepositoryScan] snapshot=%s commit=%s files=%d content_keys=%d deps=%d manifests=%d",
            snapshot_id, commit_sha[:12],
            len(files), len(file_contents), len(raw_dependencies), len(dependency_manifests)
        )

        return cls(
            snapshot_id=snapshot_id,
            commit_sha=commit_sha,
            github_url=github_url,
            repository_name=repository_name,
            files=files,
            file_contents=file_contents,
            dependency_manifests=dependency_manifests,
            raw_dependencies=raw_dependencies,
            folder_structure_raw=folder_structure_raw,
        )

    @classmethod
    def _load_github_cache(cls, github_url: str, known_files: List[str]) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        Load file contents and dependency manifests from the GitHub tool disk cache.
        Returns (file_contents, dependency_manifests).
        """
        file_contents: Dict[str, str] = {}
        dependency_manifests: Dict[str, str] = {}

        MANIFEST_NAMES = {
            "requirements.txt", "pyproject.toml", "Pipfile", "Pipfile.lock",
            "package.json", "yarn.lock", "package-lock.json",
            "go.mod", "go.sum",
            "Cargo.toml", "Cargo.lock",
            "pom.xml", "build.gradle", "build.gradle.kts",
            "*.csproj", "*.fsproj",
            "Gemfile", "Gemfile.lock",
            "composer.json",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        }

        try:
            from tools.github_tool import _cache_path, _repo_name_from_url
            repo_name = _repo_name_from_url(github_url)
            path = _cache_path(repo_name)
            if not path.exists():
                logger.warning("[RepositoryScan] GitHub cache not found: %s", path)
                return file_contents, dependency_manifests

            payload = json.loads(path.read_text(encoding="utf-8"))
            data = payload.get("data", {})

            def add_file(fpath: str, content: str) -> None:
                if not fpath or not isinstance(content, str):
                    return
                # Normalize the path key to match folder_structure paths
                clean_path = fpath.replace("\\", "/").strip()
                file_contents[clean_path] = content
                # Check if this is a dependency manifest
                basename = clean_path.split("/")[-1]
                if basename in MANIFEST_NAMES or basename.endswith((".csproj", ".fsproj")):
                    dependency_manifests[clean_path] = content

            for item in data.get("source_files", []):
                if isinstance(item, dict):
                    add_file(item.get("path", ""), item.get("content", ""))

            for item in data.get("python_files", []):
                if isinstance(item, dict):
                    add_file(item.get("path", ""), item.get("content", ""))

            for dpath, dcontent in data.get("dependencies", {}).items():
                if isinstance(dcontent, str):
                    add_file(dpath, dcontent)

        except Exception as e:
            logger.exception("[RepositoryScan] Failed to load GitHub cache: %s", e)

        return file_contents, dependency_manifests
