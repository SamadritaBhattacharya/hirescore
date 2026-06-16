"""
Web Research Agent.

Responsibilities:
- Search for talks, articles, blog posts by the candidate
- Find hackathon participations and wins
- Detect Stack Overflow activity
- In no-JD mode: search company open roles
- Detect community signals (OSS impact, conference talks)
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from tavily import TavilyClient

from core.config import get_settings
from core.logging import get_logger
from agents.base_agent import BaseAgent
from models.schemas import AgentName, ResearchJobState, WebResearchResult

logger = get_logger(__name__)

HACKATHON_PLATFORMS = [
    "devfolio.co", "devpost.com", "unstop.com",
    "mlh.io", "kaggle.com", "topcoder.com", "hackerearth.com",
]


class WebResearchAgent(BaseAgent):
    """
    Searches the web for candidate's public footprint using Tavily API.
    Runs 3 targeted searches concurrently to respect free-tier limits.
    """

    def __init__(self) -> None:
        super().__init__(name=AgentName.WEB_RESEARCH, timeout_seconds=60)
        self._settings = get_settings()
        self._client = TavilyClient(api_key=self._settings.tavily_api_key)

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        candidate_name = self._resolve_candidate_name(state)
        company_name = self._extract_company_name(state)

        queries = self._build_queries(
            candidate_name=candidate_name,
            company_name=company_name,
            has_jd=bool(state.input.jd_text),
        )

        # Run all searches concurrently
        results = await asyncio.gather(
            *[self._search(q["query"], q["label"]) for q in queries],
            return_exceptions=True,
        )

        web_result = WebResearchResult()
        for query_meta, result in zip(queries, results):
            if isinstance(result, Exception):
                logger.warning(
                    "search_failed",
                    query=query_meta["query"],
                    error=str(result),
                )
                continue
            self._process_results(
                result,
                label=query_meta["label"],
                web_result=web_result,
                candidate_name=candidate_name,
            )

        state.web_research_data = web_result
        return state

    def _resolve_candidate_name(self, state: ResearchJobState) -> str:
        """Best-effort candidate name extraction from available inputs."""
        if state.linkedin_data and state.linkedin_data.name:
            return state.linkedin_data.name
        if state.input.resume_text:
            # Try to extract name from first line of resume
            first_line = state.input.resume_text.strip().split("\n")[0]
            if len(first_line) < 60:
                return first_line.strip()
        return "candidate"

    def _extract_company_name(self, state: ResearchJobState) -> str:
        """Try to extract company name from culture doc or JD."""
        for text in [state.input.culture_doc_text, state.input.jd_text]:
            if text:
                # Look for "Company: X" or "About X" patterns
                for pattern in [
                    r"(?:company|organization|about)\s*[:\-]\s*([A-Z][A-Za-z\s]{2,40})",
                    r"^([A-Z][A-Za-z\s]{2,30})\s+is\s+(?:a|an)\s+",
                ]:
                    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        return match.group(1).strip()
        return ""

    def _build_queries(
        self,
        candidate_name: str,
        company_name: str,
        has_jd: bool,
    ) -> list[dict[str, str]]:
        """
        Build 3 targeted search queries.
        Conservative: 3 searches per job to stay within free tier (1000/month).
        """
        queries = [
            {
                "label": "technical_presence",
                "query": (
                    f'"{candidate_name}" site:medium.com OR site:dev.to '
                    f'OR site:stackoverflow.com OR site:hashnode.com'
                ),
            },
            {
                "label": "hackathons_community",
                "query": (
                    f'"{candidate_name}" hackathon OR "open source" '
                    f'OR devfolio OR devpost OR kaggle'
                ),
            },
        ]

        if not has_jd and company_name:
            queries.append({
                "label": "company_roles",
                "query": f'site:{self._guess_company_domain(company_name)} careers OR jobs',
            })
        else:
            queries.append({
                "label": "talks_articles",
                "query": (
                    f'"{candidate_name}" talk OR conference OR "tech blog" '
                    f'OR speaker OR presentation'
                ),
            })

        return queries

    def _guess_company_domain(self, company_name: str) -> str:
        slug = company_name.lower().replace(" ", "")
        return f"{slug}.com"

    async def _search(self, query: str, label: str) -> list[dict[str, Any]]:
        """Run a single Tavily search asynchronously."""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.search(
                query=query,
                max_results=self._settings.tavily_max_results,
                search_depth="basic",
                include_answer=False,
            ),
        )
        return response.get("results", [])

    def _process_results(
        self,
        results: list[dict[str, Any]],
        label: str,
        web_result: WebResearchResult,
        candidate_name: str,
    ) -> None:
        """Route search results into the appropriate WebResearchResult fields."""
        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            snippet = item.get("content", "")[:300]

            entry = {"title": title, "url": url, "snippet": snippet}

            if label == "technical_presence":
                if "stackoverflow.com" in url:
                    web_result.stackoverflow_profile = entry
                elif any(b in url for b in ["medium.com", "dev.to", "hashnode", "substack"]):
                    web_result.articles.append(entry)
                else:
                    web_result.community_signals.append(title)

            elif label == "hackathons_community":
                if any(p in url for p in HACKATHON_PLATFORMS):
                    web_result.hackathons.append(entry)
                elif "github.com" in url and "pulls" in url:
                    web_result.open_source_impact.append(title)
                else:
                    web_result.community_signals.append(title)

            elif label == "talks_articles":
                if any(
                    kw in url.lower() for kw in ["talk", "speak", "conf", "youtube"]
                ):
                    web_result.talks.append(entry)
                else:
                    web_result.articles.append(entry)

            elif label == "company_roles":
                web_result.company_open_roles.append(entry)

        # Deduplicate lists
        web_result.community_signals = list(dict.fromkeys(web_result.community_signals))[:10]