"""
GitHub Research Agent.

Responsibilities:
- Extract GitHub username from URL
- Fetch repos, languages, stars, commit activity
- Detect AI/ML repos and open source contributions
- Produce structured GitHubProfile
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import get_settings
from core.logging import get_logger
from graph.base_agent import BaseAgent
from models.schemas import AgentName, GitHubProfile, ResearchJobState

logger = get_logger(__name__)

AI_ML_TOPICS = {
    "machine-learning", "deep-learning", "neural-network", "nlp",
    "computer-vision", "transformers", "llm", "pytorch", "tensorflow",
    "keras", "scikit-learn", "huggingface", "langchain", "openai",
    "reinforcement-learning", "diffusion-model", "generative-ai",
    "rag", "vector-database", "embedding", "fine-tuning",
}

AI_ML_KEYWORDS = {
    "model", "training", "inference", "dataset", "embedding",
    "transformer", "attention", "bert", "gpt", "llama", "mistral",
    "agent", "langgraph", "langchain", "chromadb", "faiss",
}


class GitHubAgent(BaseAgent):
    """
    Fetches candidate data from GitHub REST API.
    Uses authenticated requests when token is available (5000 req/hr).
    Falls back to unauthenticated (60 req/hr) gracefully.
    """

    def __init__(self) -> None:
        super().__init__(name=AgentName.GITHUB, timeout_seconds=45)
        self._settings = get_settings()
        self._base_url = "https://api.github.com"
        self._headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._settings.github_authenticated:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        return headers

    @staticmethod
    def extract_username(github_url: str) -> str | None:
        """Extract GitHub username from URL."""
        patterns = [
            r"github\.com/([A-Za-z0-9\-_]+)/?",
            r"^([A-Za-z0-9\-_]+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, str(github_url))
            if match:
                username = match.group(1)
                if username.lower() not in {"orgs", "repos", "topics", "trending"}:
                    return username
        return None

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        if not state.input.github_url:
            logger.info("github_skipped", reason="no_url", job_id=str(state.job_id))
            return state

        username = self.extract_username(str(state.input.github_url))
        if not username:
            state.errors[self.name.value] = "Could not extract GitHub username from URL"
            return state

        async with httpx.AsyncClient(
            headers=self._headers,
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            profile = await self._build_profile(client, username)

        state.github_data = profile
        return state

    async def _build_profile(
        self, client: httpx.AsyncClient, username: str
    ) -> GitHubProfile:
        """Orchestrate all GitHub API calls and build the profile."""
        user_data = await self._fetch_user(client, username)
        repos = await self._fetch_repos(client, username)
        recent_commits = await self._count_recent_commits(client, username, repos)
        language_breakdown = self._compute_language_breakdown(repos)
        top_languages = sorted(
            language_breakdown, key=lambda k: language_breakdown[k], reverse=True
        )[:5]

        return GitHubProfile(
            username=username,
            name=user_data.get("name") or username,
            bio=user_data.get("bio") or "",
            public_repos=user_data.get("public_repos", 0),
            followers=user_data.get("followers", 0),
            total_stars=sum(r.get("stargazers_count", 0) for r in repos),
            top_languages=top_languages,
            language_breakdown=language_breakdown,
            repos=self._summarize_repos(repos),
            recent_commit_count_90d=recent_commits,
            has_ai_ml_repos=self._detect_ai_ml(repos),
            open_source_contributions=await self._fetch_oss_contributions(
                client, username
            ),
            pinned_repos=self._get_top_repos(repos),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _fetch_user(
        self, client: httpx.AsyncClient, username: str
    ) -> dict[str, Any]:
        response = await client.get(f"{self._base_url}/users/{username}")
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _fetch_repos(
        self, client: httpx.AsyncClient, username: str
    ) -> list[dict[str, Any]]:
        """Fetch up to 100 most recently updated repos."""
        response = await client.get(
            f"{self._base_url}/users/{username}/repos",
            params={"sort": "updated", "per_page": 100, "type": "owner"},
        )
        response.raise_for_status()
        return response.json()

    async def _count_recent_commits(
        self,
        client: httpx.AsyncClient,
        username: str,
        repos: list[dict[str, Any]],
    ) -> int:
        """Count commits across top-5 active repos in the last 90 days."""
        cutoff = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        active_repos = sorted(
            repos,
            key=lambda r: r.get("pushed_at") or "",
            reverse=True,
        )[:5]

        total = 0
        for repo in active_repos:
            try:
                response = await client.get(
                    f"{self._base_url}/repos/{username}/{repo['name']}/commits",
                    params={"author": username, "since": cutoff, "per_page": 100},
                )
                if response.status_code == 200:
                    commits = response.json()
                    total += len(commits) if isinstance(commits, list) else 0
            except Exception:
                continue
        return total

    async def _fetch_oss_contributions(
        self, client: httpx.AsyncClient, username: str
    ) -> list[str]:
        """Find repos the user contributed to but doesn't own."""
        try:
            response = await client.get(
                f"{self._base_url}/search/commits",
                params={
                    "q": f"author:{username} -user:{username}",
                    "per_page": 10,
                },
                headers={**self._headers, "Accept": "application/vnd.github.cloak-preview"},
            )
            if response.status_code != 200:
                return []
            items = response.json().get("items", [])
            return list(
                {
                    item["repository"]["full_name"]
                    for item in items
                    if "repository" in item
                }
            )[:10]
        except Exception:
            return []

    def _compute_language_breakdown(
        self, repos: list[dict[str, Any]]
    ) -> dict[str, float]:
        counts: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language")
            if lang:
                counts[lang] = counts.get(lang, 0) + 1
        total = sum(counts.values()) or 1
        return {lang: round(count / total * 100, 1) for lang, count in counts.items()}

    def _detect_ai_ml(self, repos: list[dict[str, Any]]) -> bool:
        for repo in repos:
            # Check topics
            topics = set(repo.get("topics") or [])
            if topics & AI_ML_TOPICS:
                return True
            # Check repo name and description
            text = f"{repo.get('name','')} {repo.get('description','')}".lower()
            if any(kw in text for kw in AI_ML_KEYWORDS):
                return True
        return False

    def _summarize_repos(
        self, repos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": r.get("name", ""),
                "description": r.get("description") or "",
                "language": r.get("language") or "",
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "topics": r.get("topics") or [],
                "updated_at": r.get("updated_at") or "",
                "url": r.get("html_url") or "",
            }
            for r in repos[:30]
        ]

    def _get_top_repos(
        self, repos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return top 5 repos by stars."""
        sorted_repos = sorted(
            repos,
            key=lambda r: r.get("stargazers_count", 0),
            reverse=True,
        )
        return self._summarize_repos(sorted_repos[:5])