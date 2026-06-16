"""
LinkedIn Research Agent.

Strategy (in order):
1. If linkedin_text is provided → parse directly (most reliable)
2. If resume_text is provided → extract LinkedIn-equivalent data from resume
3. If linkedin_url is provided → attempt scrape (may be blocked)
4. Fallback → minimal profile with what we have

This layered approach ensures the pipeline never hard-fails on LinkedIn.
"""

from __future__ import annotations

import re
from typing import Any

from core.config import get_settings
from core.logging import get_logger
from agents.base_agent import BaseAgent
from models.schemas import AgentName, LinkedInProfile, ResearchJobState

logger = get_logger(__name__)


class LinkedInAgent(BaseAgent):
    """
    Extracts candidate profile data from LinkedIn.
    Prioritizes pre-parsed text over live scraping for reliability.
    """

    def __init__(self) -> None:
        super().__init__(name=AgentName.LINKEDIN, timeout_seconds=30)
        self._settings = get_settings()

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        profile: LinkedInProfile | None = None

        # Strategy 1: parse pasted LinkedIn text
        if state.input.linkedin_text:
            logger.info("linkedin_parse_strategy", strategy="text_paste")
            profile = self._parse_text(state.input.linkedin_text, source="text_paste")

        # Strategy 2: extract from resume
        elif state.input.resume_text:
            logger.info("linkedin_parse_strategy", strategy="resume_fallback")
            profile = self._parse_resume(state.input.resume_text)

        # Strategy 3: attempt live scrape
        # elif state.input.linkedin_url and self._settings.linkedin_scraper_enabled:
        #     logger.info("linkedin_parse_strategy", strategy="scrape")
        #     profile = await self._scrape(str(state.input.linkedin_url))

        # Strategy 4: minimal profile from URL only
        if profile is None:
            logger.warning("linkedin_parse_fallback", strategy="minimal")
            profile = LinkedInProfile(source="unavailable")

        state.linkedin_data = profile
        return state

    def _parse_text(self, text: str, source: str = "text_paste") -> LinkedInProfile:
        """
        Parse pasted LinkedIn profile text.
        Users export their profile as PDF or copy-paste it.
        This handles typical LinkedIn export text format.
        """
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        profile = LinkedInProfile(source=source)

        if not lines:
            return profile

        # First non-empty line is usually the name
        profile.name = lines[0] if lines else ""

        # Second line is usually the headline
        if len(lines) > 1:
            profile.headline = lines[1]

        # Extract location (often "City, Country" format)
        for line in lines[:10]:
            if re.search(r"[A-Z][a-z]+,\s+[A-Z]", line):
                profile.location = line
                break

        # Extract skills section
        profile.skills = self._extract_skills(text)

        # Extract experience years
        profile.total_experience_years = self._estimate_experience_years(text)

        # Extract current role/company
        current = self._extract_current_role(lines)
        profile.current_role = current.get("role", "")
        profile.current_company = current.get("company", "")

        # Extract certifications
        profile.certifications = self._extract_certifications(text)

        # Summary / About section
        about_idx = self._find_section(lines, ["about", "summary"])
        if about_idx >= 0 and about_idx + 1 < len(lines):
            profile.summary = " ".join(lines[about_idx + 1 : about_idx + 6])

        return profile

    def _parse_resume(self, resume_text: str) -> LinkedInProfile:
        """Extract LinkedIn-equivalent data from resume text."""
        profile = self._parse_text(resume_text, source="resume_fallback")
        return profile

    # async def _scrape(self, url: str) -> LinkedInProfile | None:
    #     """
    #     Attempt LinkedIn scraping using linkedin-scraper.
    #     This may fail due to LinkedIn's anti-bot measures.
    #     Returns None on failure so caller can fall back.
    #     """
    #     try:
    #         from linkedin_scraper import Person, actions
    #         from selenium import webdriver
    #         from selenium.webdriver.chrome.options import Options
    #         from webdriver_manager.chrome import ChromeDriverManager
    #         from selenium.webdriver.chrome.service import Service

    #         options = Options()
    #         options.add_argument("--headless")
    #         options.add_argument("--no-sandbox")
    #         options.add_argument("--disable-dev-shm-usage")
    #         options.add_argument("--disable-gpu")

    #         driver = webdriver.Chrome(
    #             service=Service(ChromeDriverManager().install()),
    #             options=options,
    #         )

    #         try:
    #             actions.login(
    #                 driver,
    #                 self._settings.linkedin_email,
    #                 self._settings.linkedin_password,
    #             )
    #             person = Person(url, driver=driver, close_on_complete=False)

    #             profile = LinkedInProfile(
    #                 name=person.name or "",
    #                 headline=getattr(person, "headline", "") or "",
    #                 location=getattr(person, "location", "") or "",
    #                 current_role=person.job_title or "",
    #                 current_company=person.company or "",
    #                 skills=[s for s in (getattr(person, "skills", []) or [])],
    #                 source="scrape",
    #             )
    #             profile.total_experience_years = self._estimate_experience_years(
    #                 " ".join([e.get("date_range", "") for e in (getattr(person, "experiences", []) or [])])
    #             )
    #             return profile
    #         finally:
    #             driver.quit()

    #     except ImportError:
    #         logger.warning("linkedin_scraper_not_installed")
    #         return None
    #     except Exception as exc:
    #         logger.warning("linkedin_scrape_failed", error=str(exc))
    #         return None

    # --- Text extraction helpers ---

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skills from skills section or inline mentions."""
        skills: list[str] = []

        # Find skills section
        skills_pattern = re.compile(
            r"(?:skills|technical skills|technologies|tools)\s*[:\n](.{0,2000}?)(?:\n[A-Z]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        match = skills_pattern.search(text)
        if match:
            raw = match.group(1)
            # Split by common delimiters
            parts = re.split(r"[,•|·\n·–\-]+", raw)
            skills = [p.strip() for p in parts if 2 < len(p.strip()) < 40]

        # Fallback: known tech keywords
        if len(skills) < 3:
            TECH_KEYWORDS = [
                "Python", "JavaScript", "TypeScript", "React", "Node.js",
                "FastAPI", "Django", "Flask", "SQL", "PostgreSQL", "MongoDB",
                "Docker", "Kubernetes", "AWS", "GCP", "Azure", "LangChain",
                "LangGraph", "PyTorch", "TensorFlow", "Scikit-learn", "Pandas",
                "NumPy", "Git", "Linux", "REST", "GraphQL", "Redis", "Kafka",
                "Spark", "Airflow", "dbt", "Hugging Face", "OpenAI", "Groq",
                "ChromaDB", "Pinecone", "FAISS", "RAG", "LLM", "ML", "AI",
            ]
            found = [kw for kw in TECH_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE)]
            skills = list(dict.fromkeys(skills + found))

        return skills[:30]

    def _estimate_experience_years(self, text: str) -> float:
        """
        Estimate total years of experience from date ranges.
        Looks for patterns like "2019 – 2023", "Jan 2020 - Present".
        """
        year_pattern = re.compile(r"\b(20\d{2}|19\d{2})\b")
        years = [int(y) for y in year_pattern.findall(text)]
        if len(years) >= 2:
            return float(max(years) - min(years))
        return 0.0

    def _extract_current_role(self, lines: list[str]) -> dict[str, str]:
        """Heuristic: find experience section and grab first role."""
        exp_idx = self._find_section(lines, ["experience", "work experience", "employment"])
        if exp_idx >= 0 and exp_idx + 2 < len(lines):
            return {
                "role": lines[exp_idx + 1],
                "company": lines[exp_idx + 2] if exp_idx + 2 < len(lines) else "",
            }
        return {"role": "", "company": ""}

    def _extract_certifications(self, text: str) -> list[str]:
        cert_pattern = re.compile(
            r"(?:certifications?|licenses?)\s*[:\n](.{0,1000}?)(?:\n[A-Z]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        match = cert_pattern.search(text)
        if match:
            raw = match.group(1)
            certs = [c.strip() for c in re.split(r"[\n•·]+", raw) if len(c.strip()) > 5]
            return certs[:10]
        return []

    def _find_section(self, lines: list[str], keywords: list[str]) -> int:
        """Return index of line that matches any section keyword."""
        for i, line in enumerate(lines):
            if line.lower().strip() in keywords:
                return i
        return -1