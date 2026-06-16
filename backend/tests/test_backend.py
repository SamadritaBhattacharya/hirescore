"""
Smoke tests for HireScope backend.
Run with: pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pytest
from pydantic import ValidationError

from models.schemas import (
    ResearchInput,
    ResearchJobState,
    GitHubProfile,
    LinkedInProfile,
    FitScoreResult,
    HireVerdict,
    RoleArchetype,
    ScoreBreakdown,
    JobStatus,
    AgentName,
)
from parsers.document_parser import DocumentParserFactory, PDFParser, DOCXParser, PlainTextParser
from agents.routing_agent import RoutingAgent
from agents.github_agent import GitHubAgent


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

class TestResearchInput:

    def test_valid_with_linkedin_url(self):
        inp = ResearchInput(linkedin_url="https://linkedin.com/in/johndoe")
        assert inp.linkedin_url is not None

    def test_valid_with_linkedin_text(self):
        inp = ResearchInput(linkedin_text="John Doe\nSoftware Engineer\nSkills: Python")
        assert inp.linkedin_text is not None

    def test_fails_without_linkedin_source(self):
        with pytest.raises(ValidationError):
            ResearchInput(github_url="https://github.com/johndoe")

    def test_strips_whitespace(self):
        inp = ResearchInput(linkedin_text="  John Doe  ")
        assert inp.linkedin_text == "John Doe"

    def test_empty_github_url_becomes_none(self):
        inp = ResearchInput(linkedin_url="https://linkedin.com/in/x", github_url="")
        assert inp.github_url is None

    def test_full_input(self):
        inp = ResearchInput(
            linkedin_url="https://linkedin.com/in/johndoe",
            github_url="https://github.com/johndoe",
            jd_text="We need a Python developer with 3+ years experience",
            culture_doc_text="We value ownership and learning",
            resume_text="John Doe\nPython, FastAPI, PostgreSQL\n2019-2024",
            extra_context="Referred by team lead",
        )
        assert inp.jd_text is not None
        assert inp.culture_doc_text is not None


class TestResearchJobState:

    def test_default_status_is_pending(self):
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        assert state.status == JobStatus.PENDING

    def test_job_id_is_uuid(self):
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        assert state.job_id is not None

    def test_agents_to_run_starts_empty(self):
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        assert state.agents_to_run == []


class TestScoreBreakdown:

    def test_score_bounds(self):
        b = ScoreBreakdown(
            skill_match_score=0.75,
            experience_match_score=0.6,
            project_relevance_score=0.5,
            activity_score=0.4,
        )
        assert 0.0 <= b.skill_match_score <= 1.0

    def test_invalid_score_raises(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(skill_match_score=1.5)  # > 1.0


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------

class TestPlainTextParser:

    def test_parse_utf8(self):
        parser = PlainTextParser()
        result = parser.parse(b"Hello World", "test.txt")
        assert result == "Hello World"

    def test_parse_empty(self):
        parser = PlainTextParser()
        result = parser.parse(b"", "empty.txt")
        assert result == ""


class TestDocumentParserFactory:

    def test_txt_returns_plain_text_parser(self):
        parser = DocumentParserFactory.get_parser("resume.txt")
        assert isinstance(parser, PlainTextParser)

    def test_md_returns_plain_text_parser(self):
        parser = DocumentParserFactory.get_parser("notes.md")
        assert isinstance(parser, PlainTextParser)

    def test_unknown_extension_falls_back(self):
        parser = DocumentParserFactory.get_parser("file.xyz")
        assert isinstance(parser, PlainTextParser)

    def test_pdf_returns_pdf_parser(self):
        parser = DocumentParserFactory.get_parser("resume.pdf")
        assert isinstance(parser, PDFParser)

    def test_docx_returns_docx_parser(self):
        parser = DocumentParserFactory.get_parser("resume.docx")
        assert isinstance(parser, DOCXParser)

    def test_parse_text_convenience(self):
        result = DocumentParserFactory.parse(b"Python developer", "jd.txt")
        assert "Python" in result


# ---------------------------------------------------------------------------
# Routing Agent Tests
# ---------------------------------------------------------------------------

class TestRoutingAgent:

    @pytest.mark.asyncio
    async def test_routes_linkedin_always(self):
        agent = RoutingAgent()
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        result = await agent.run(state)
        assert AgentName.LINKEDIN in result.agents_to_run

    @pytest.mark.asyncio
    async def test_routes_github_when_url_given(self):
        agent = RoutingAgent()
        state = ResearchJobState(
            input=ResearchInput(
                linkedin_url="https://linkedin.com/in/x",
                github_url="https://github.com/johndoe",
            )
        )
        result = await agent.run(state)
        assert AgentName.GITHUB in result.agents_to_run

    @pytest.mark.asyncio
    async def test_skips_github_when_no_url(self):
        agent = RoutingAgent()
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        result = await agent.run(state)
        assert AgentName.GITHUB not in result.agents_to_run

    @pytest.mark.asyncio
    async def test_always_includes_synthesizer(self):
        agent = RoutingAgent()
        state = ResearchJobState(
            input=ResearchInput(linkedin_url="https://linkedin.com/in/x")
        )
        result = await agent.run(state)
        assert AgentName.SYNTHESIZER in result.agents_to_run
        assert AgentName.FIT_SCORER in result.agents_to_run


# ---------------------------------------------------------------------------
# GitHub Agent Unit Tests (no network)
# ---------------------------------------------------------------------------

class TestGitHubAgentUtils:

    def test_extract_username_from_url(self):
        agent = GitHubAgent()
        assert agent.extract_username("https://github.com/johndoe") == "johndoe"
        assert agent.extract_username("https://github.com/johndoe/") == "johndoe"
        assert agent.extract_username("github.com/johndoe") == "johndoe"

    def test_extract_username_invalid(self):
        agent = GitHubAgent()
        assert agent.extract_username("https://github.com/orgs") is None

    def test_language_breakdown(self):
        agent = GitHubAgent()
        repos = [
            {"language": "Python"},
            {"language": "Python"},
            {"language": "JavaScript"},
            {"language": None},
        ]
        breakdown = agent._compute_language_breakdown(repos)
        assert breakdown["Python"] > breakdown["JavaScript"]
        assert "None" not in breakdown

    def test_detect_ai_ml_repos_by_topic(self):
        agent = GitHubAgent()
        repos = [{"topics": ["llm", "rag"], "name": "myapp", "description": ""}]
        assert agent._detect_ai_ml(repos) is True

    def test_detect_ai_ml_repos_by_keyword(self):
        agent = GitHubAgent()
        repos = [{"topics": [], "name": "llama-finetune", "description": "Fine-tuning"}]
        assert agent._detect_ai_ml(repos) is True

    def test_no_ai_ml_repos(self):
        agent = GitHubAgent()
        repos = [{"topics": [], "name": "todo-app", "description": "Simple todo"}]
        assert agent._detect_ai_ml(repos) is False


# ---------------------------------------------------------------------------
# LinkedIn Agent Text Parsing Tests
# ---------------------------------------------------------------------------

class TestLinkedInAgentParsing:

    def test_parse_basic_profile(self):
        from agents.linkedin_agent import LinkedInAgent
        agent = LinkedInAgent()
        text = """John Doe
Senior ML Engineer at TechCorp
Mumbai, India

About
Building AI products at scale using LangChain and PyTorch.

Skills
Python · PyTorch · LangChain · FastAPI · Docker · AWS

Experience
Senior ML Engineer
TechCorp
2021 - Present

Education
B.Tech Computer Science
IIT Bombay
2017 - 2021"""

        profile = agent._parse_text(text)
        assert profile.name == "John Doe"
        assert "Python" in profile.skills or len(profile.skills) > 0
        assert profile.total_experience_years >= 0

    def test_estimate_experience_years(self):
        from agents.linkedin_agent import LinkedInAgent
        agent = LinkedInAgent()
        text = "Software Engineer 2019 - 2024 at Company"
        years = agent._estimate_experience_years(text)
        assert years == 5.0