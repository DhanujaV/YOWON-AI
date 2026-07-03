"""
git_provider.py — Abstract Git Provider interface and GitHub implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from github import Github, GithubException
from config import GITHUB_TOKEN
from security import validate_github_url


class GitProvider(ABC):
    """Abstract interface defining required repository extraction operations."""

    @abstractmethod
    def get_repo_details(self, url: str) -> dict[str, Any]:
        """Extract repository metadata."""
        pass

    @abstractmethod
    def get_latest_commit(self, url: str, branch: Optional[str] = None) -> dict[str, Any]:
        """Fetch details of the latest commit on a branch."""
        pass

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> Optional[dict[str, Any]]:
        """Parse webhook event payloads into normalized updates."""
        pass


class GitHubProvider(GitProvider):
    """GitHub integration wrapping PyGithub client."""

    def __init__(self, token: Optional[str] = GITHUB_TOKEN):
        self.token = token
        self.client = Github(token) if token else Github()

    def _repo_name_from_url(self, url: str) -> str:
        safe_url = validate_github_url(url)
        if not safe_url:
            raise ValueError(f"Invalid URL: {url}")
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", str(safe_url).rstrip("/"))
        if not match:
            raise ValueError(f"Cannot parse GitHub repo name from URL: {url}")
        return match.group(1)

    def get_repo_details(self, url: str) -> dict[str, Any]:
        repo_name = self._repo_name_from_url(url)
        try:
            repo = self.client.get_repo(repo_name)
            license_key = None
            try:
                lic = repo.get_license()
                license_key = lic.license.key if lic and lic.license else None
            except Exception:
                pass

            return {
                "github_repository_id": str(repo.id),
                "owner": repo.owner.login,
                "repository_name": repo.name,
                "github_url": repo.html_url,
                "default_branch": repo.default_branch,
                "visibility": "private" if repo.private else "public",
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "license": license_key,
                "topics": json.dumps(repo.get_topics()),
            }
        except GithubException as exc:
            raise RuntimeError(f"GitHub API Error: {exc.data.get('message', str(exc))}") from exc

    def get_latest_commit(self, url: str, branch: Optional[str] = None) -> dict[str, Any]:
        repo_name = self._repo_name_from_url(url)
        try:
            repo = self.client.get_repo(repo_name)
            target_branch = branch or repo.default_branch
            git_branch = repo.get_branch(target_branch)
            commit_sha = git_branch.commit.sha
            
            # Fetch tree SHA
            tree_sha = None
            try:
                tree_sha = repo.get_git_tree(commit_sha).sha
            except Exception:
                pass

            # Fetch last commit timestamp
            last_commit_timestamp = None
            try:
                commit_details = repo.get_commit(commit_sha)
                last_commit_timestamp = commit_details.commit.author.date
            except Exception:
                pass

            return {
                "commit_sha": commit_sha,
                "tree_sha": tree_sha,
                "branch": target_branch,
                "last_commit_timestamp": last_commit_timestamp,
            }
        except GithubException as exc:
            raise RuntimeError(f"GitHub API Error: {exc.data.get('message', str(exc))}") from exc

    def parse_webhook(self, payload: dict[str, Any], headers: dict[str, str]) -> Optional[dict[str, Any]]:
        # Handle GitHub ping event
        event_type = headers.get("X-GitHub-Event", "push")
        if event_type == "ping":
            return {"type": "ping", "message": "Connection active"}

        if event_type != "push":
            return None

        # Verify refs/heads/branch or tag
        ref = payload.get("ref", "")
        if not ref.startswith("refs/heads/"):
            return None

        branch = ref.removeprefix("refs/heads/")
        repo_data = payload.get("repository", {})
        github_url = repo_data.get("html_url")
        head_commit = payload.get("head_commit", {})
        commit_sha = head_commit.get("id")

        if not github_url or not commit_sha:
            return None

        return {
            "type": "push",
            "github_url": github_url,
            "commit_sha": commit_sha,
            "branch": branch,
            "github_repository_id": str(repo_data.get("id", "")),
        }
