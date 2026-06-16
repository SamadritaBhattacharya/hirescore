"""
Pydantic v2 schemas for HireScope.

Design principles:
- Immutable by default (frozen where safe)
- Strict typing throughout
- Clear separation: Input → Intermediate → Output
- No Optional fields without explicit None default
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    PENDING = "pending"
    ROUTING = "routing"
    RESEARCHING = "researching"
    SCORING = "scoring"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentName(str, Enum):
    ROUTING = "routing"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    WEB_RESEARCH = "web_research"
    FIT_SCORER = "fit_scorer"
    SYNTHESIZER = "synthesizer"


class RoleArchetype(str, Enum):
    ML_ENGINEER = "ML Engineer"
    BACKEND_ENGINEER = "Backend Engineer"
    FRONTEND_ENGINEER = "Frontend Engineer"
    FULLSTACK_ENGINEER = "Full Stack Engineer"
    DATA_SCIENTIST = "Data Scientist"
    DATA_ENGINEER = "Data Engineer"
    DEVOPS_ENGINEER = "DevOps / MLOps Engineer"
    PRODUCT_MANAGER = "Product Manager"
    RESEARCH_SCIENTIST = "Research Scientist"
    UNKNOWN = "Unknown"


class HireVerdict(str, Enum):
    STRONG_YES = "Strong Yes"
    YES = "Yes"
    MAYBE = "Maybe"
    NO = "No"
    STRONG_NO = "Strong No"


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------


class ResearchInput(BaseModel):
    """
    Primary input payload from the HR user.
    At least one of linkedin_url or linkedin_text is required.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Candidate identifiers
    linkedin_url: HttpUrl | None = Field(
        default=None,
        description="Candidate LinkedIn profile URL",
        examples=["https://linkedin.com/in/johndoe"],
    )
    linkedin_text: str | None = Field(
        default=None,
        description="Pasted LinkedIn profile text (fallback if scraping blocked)",
        max_length=20_000,
    )
    github_url: HttpUrl | None = Field(
        default=None,
        description="Candidate GitHub profile URL",
        examples=["https://github.com/johndoe"],
    )

    # Documents (raw text after parsing)
    resume_text: str | None = Field(
        default=None,
        description="Extracted text from uploaded resume",
        max_length=50_000,
    )
    jd_text: str | None = Field(
        default=None,
        description="Job description text",
        max_length=20_000,
    )
    culture_doc_text: str | None = Field(
        default=None,
        description="Company culture document text",
        max_length=20_000,
    )
    extra_context: str | None = Field(
        default=None,
        description="Additional HR context or notes",
        max_length=5_000,
    )

    @model_validator(mode="after")
    def require_linkedin_source(self) -> ResearchInput:
        if not self.linkedin_url and not self.linkedin_text:
            raise ValueError(
                "At least one of 'linkedin_url' or 'linkedin_text' is required."
            )
        return self

    @field_validator("github_url", "linkedin_url", mode="before")
    @classmethod
    def coerce_empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


# ---------------------------------------------------------------------------
# Intermediate / Agent Output Models
# ---------------------------------------------------------------------------


class LinkedInProfile(BaseModel):
    """Structured data extracted by the LinkedIn agent."""

    name: str = ""
    headline: str = ""
    location: str = ""
    summary: str = ""
    current_role: str = ""
    current_company: str = ""
    total_experience_years: float = 0.0
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    education: list[dict[str, str]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "unknown"  # "scrape" | "text_parse" | "resume_fallback"


class GitHubProfile(BaseModel):
    """Structured data extracted by the GitHub agent."""

    username: str = ""
    name: str = ""
    bio: str = ""
    public_repos: int = 0
    followers: int = 0
    total_stars: int = 0
    top_languages: list[str] = Field(default_factory=list)
    language_breakdown: dict[str, float] = Field(default_factory=dict)  # lang → %
    repos: list[dict[str, Any]] = Field(default_factory=list)
    recent_commit_count_90d: int = 0
    contribution_streak_days: int = 0
    has_ai_ml_repos: bool = False
    open_source_contributions: list[str] = Field(default_factory=list)
    pinned_repos: list[dict[str, Any]] = Field(default_factory=list)


class WebResearchResult(BaseModel):
    """Structured data from web research agent."""

    talks: list[dict[str, str]] = Field(default_factory=list)
    articles: list[dict[str, str]] = Field(default_factory=list)
    stackoverflow_profile: dict[str, Any] = Field(default_factory=dict)
    hackathons: list[dict[str, str]] = Field(default_factory=list)
    open_source_impact: list[str] = Field(default_factory=list)
    community_signals: list[str] = Field(default_factory=list)
    company_open_roles: list[dict[str, str]] = Field(default_factory=list)  # no-JD mode


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of hire score components."""

    skill_match_score: float = Field(ge=0.0, le=1.0, default=0.0)
    experience_match_score: float = Field(ge=0.0, le=1.0, default=0.0)
    project_relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    activity_score: float = Field(ge=0.0, le=1.0, default=0.0)

    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    extra_skills: list[str] = Field(default_factory=list)  # candidate has beyond JD

    skill_match_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    experience_years_candidate: float = 0.0
    experience_years_required: float = 0.0

    reasoning: str = ""  # LLM explanation of the score


class FitScoreResult(BaseModel):
    """Output from the Fit Scorer agent."""

    hire_score: Annotated[int, Field(ge=0, le=100)] = 0
    hire_verdict: HireVerdict = HireVerdict.MAYBE
    role_fit: str = ""  # specific role if JD given, or archetype
    best_fit_archetype: RoleArchetype = RoleArchetype.UNKNOWN
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    culture_fit_score: Annotated[int, Field(ge=0, le=100)] = 0
    culture_fit_reasoning: str = ""
    jd_mode: bool = False  # True if JD was provided


class CandidateFlag(BaseModel):
    """A single green or red flag."""

    label: str
    evidence: str
    weight: str = "medium"  # "high" | "medium" | "low"


class SynthesisResult(BaseModel):
    """Final synthesized report from Synthesizer agent."""

    executive_summary: str = ""
    green_flags: list[CandidateFlag] = Field(default_factory=list)
    red_flags: list[CandidateFlag] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    suggested_role: str = ""
    detailed_analysis: str = ""


# ---------------------------------------------------------------------------
# Job / State Models (LangGraph state)
# ---------------------------------------------------------------------------


class AgentProgress(BaseModel):
    """Progress event for SSE streaming."""

    agent: AgentName
    status: str  # "started" | "completed" | "failed"
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResearchJobState(BaseModel):
    """
    Mutable LangGraph graph state shared across all agents.
    Each agent reads what it needs and writes its output key.
    """

    job_id: UUID = Field(default_factory=uuid4)
    input: ResearchInput

    # Agent outputs (populated as graph runs)
    linkedin_data: LinkedInProfile | None = None
    github_data: GitHubProfile | None = None
    web_research_data: WebResearchResult | None = None
    fit_score_data: FitScoreResult | None = None
    synthesis_data: SynthesisResult | None = None

    # Routing decisions
    agents_to_run: list[AgentName] = Field(default_factory=list)

    # Progress tracking
    progress_events: list[AgentProgress] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict)  # agent_name → error msg

    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# API Response Models
# ---------------------------------------------------------------------------


class ResearchJobResponse(BaseModel):
    """Response when a research job is created."""

    job_id: UUID
    status: JobStatus
    message: str = "Research job started"


class FullReport(BaseModel):
    """Complete final report returned to frontend."""

    job_id: UUID
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None

    # Candidate summary
    candidate_name: str = ""
    candidate_headline: str = ""
    candidate_location: str = ""
    candidate_current_role: str = ""

    # Core sections
    executive_summary: str = ""
    hire_score: int = 0
    hire_verdict: HireVerdict = HireVerdict.MAYBE
    score_breakdown: ScoreBreakdown | None = None
    culture_fit_score: int = 0
    culture_fit_reasoning: str = ""

    # Flags
    green_flags: list[CandidateFlag] = Field(default_factory=list)
    red_flags: list[CandidateFlag] = Field(default_factory=list)

    # Role
    suggested_role: str = ""
    role_fit: str = ""
    best_fit_archetype: RoleArchetype = RoleArchetype.UNKNOWN

    # Skills
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    extra_skills: list[str] = Field(default_factory=list)
    top_languages: list[str] = Field(default_factory=list)
    language_breakdown: dict[str, float] = Field(default_factory=dict)

    # Activity
    github_stars: int = 0
    github_repos: int = 0
    recent_commits_90d: int = 0
    hackathons: list[dict[str, str]] = Field(default_factory=list)
    community_signals: list[str] = Field(default_factory=list)

    # Interview
    interview_questions: list[str] = Field(default_factory=list)

    # Detail
    detailed_analysis: str = ""
    errors: dict[str, str] = Field(default_factory=dict)


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: str  # "progress" | "completed" | "error"
    data: dict[str, Any]