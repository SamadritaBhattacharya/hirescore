"""
Synthesizer Agent.

Responsibilities:
- Aggregate outputs from all research agents
- Generate executive summary, flags, interview questions, analysis via Groq
- Produce the final SynthesisResult
"""

from __future__ import annotations

import json

from groq import Groq

from core.config import get_settings
from core.logging import get_logger
from agents.base_agent import BaseAgent
from models.schemas import (
    AgentName,
    CandidateFlag,
    ResearchJobState,
    SynthesisResult,
)

logger = get_logger(__name__)


class SynthesizerAgent(BaseAgent):
    """
    Uses Groq LLM (Llama 3.3 70B) to synthesize all agent data
    into a human-readable, structured report.
    """

    def __init__(self) -> None:
        super().__init__(name=AgentName.SYNTHESIZER, timeout_seconds=60)
        self._settings = get_settings()
        self._groq = Groq(api_key=self._settings.groq_api_key)

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        context = self._build_context(state)

        summary = await self._generate_summary(context)
        flags = await self._generate_flags(context)
        questions = await self._generate_interview_questions(context, state)
        analysis = await self._generate_detailed_analysis(context)
        suggested_role = self._determine_suggested_role(state)

        state.synthesis_data = SynthesisResult(
            executive_summary=summary,
            green_flags=flags["green"],
            red_flags=flags["red"],
            interview_questions=questions,
            suggested_role=suggested_role,
            detailed_analysis=analysis,
        )
        return state

    def _build_context(self, state: ResearchJobState) -> str:
        """Build a comprehensive context string from all agent outputs."""
        sections: list[str] = []

        if state.linkedin_data:
            li = state.linkedin_data
            sections.append(
                f"CANDIDATE PROFILE:\n"
                f"Name: {li.name}\nHeadline: {li.headline}\n"
                f"Location: {li.location}\nCurrent: {li.current_role} at {li.current_company}\n"
                f"Experience: {li.total_experience_years} years\n"
                f"Skills: {', '.join(li.skills[:20])}\n"
                f"Certifications: {', '.join(li.certifications)}\n"
                f"Summary: {li.summary[:300]}"
            )

        if state.github_data:
            gh = state.github_data
            sections.append(
                f"GITHUB ACTIVITY:\n"
                f"Public Repos: {gh.public_repos} | Stars: {gh.total_stars} | "
                f"Followers: {gh.followers}\n"
                f"Top Languages: {', '.join(gh.top_languages)}\n"
                f"Recent Commits (90d): {gh.recent_commit_count_90d}\n"
                f"AI/ML Repos: {'Yes' if gh.has_ai_ml_repos else 'No'}\n"
                f"OSS Contributions: {', '.join(gh.open_source_contributions[:5])}\n"
                f"Top Repos: {', '.join(r['name'] for r in gh.pinned_repos[:3])}"
            )

        if state.web_research_data:
            web = state.web_research_data
            sections.append(
                f"WEB PRESENCE:\n"
                f"Hackathons: {len(web.hackathons)} found\n"
                f"Articles/Blogs: {len(web.articles)}\n"
                f"Talks/Conferences: {len(web.talks)}\n"
                f"Community Signals: {', '.join(web.community_signals[:5])}"
            )

        if state.fit_score_data:
            fs = state.fit_score_data
            sections.append(
                f"FIT ANALYSIS:\n"
                f"Hire Score: {fs.hire_score}/100 ({fs.hire_verdict.value})\n"
                f"Role Fit: {fs.role_fit}\n"
                f"Matched Skills: {', '.join(fs.breakdown.matched_skills[:10])}\n"
                f"Missing Skills: {', '.join(fs.breakdown.missing_skills[:10])}\n"
                f"Culture Fit: {fs.culture_fit_score}/100\n"
                f"Score Reasoning: {fs.breakdown.reasoning}"
            )

        if state.input.jd_text:
            sections.append(f"JOB DESCRIPTION (excerpt):\n{state.input.jd_text[:500]}")

        if state.input.extra_context:
            sections.append(f"ADDITIONAL CONTEXT:\n{state.input.extra_context}")

        return "\n\n---\n\n".join(sections)

    async def _generate_summary(self, context: str) -> str:
        prompt = f"""Based on this candidate research data, write a 3-4 sentence executive summary.
Be concise, factual, and professional. Mention their key strengths, experience level, and overall fit signal.
Do NOT mention gender, age, nationality, or any demographic factors.

{context}

Executive Summary:"""

        return self._call_groq(prompt, max_tokens=300)

    async def _generate_flags(
        self, context: str
    ) -> dict[str, list[CandidateFlag]]:
        prompt = f"""Based on this candidate data, identify exactly 5 green flags and 5 red flags.
Each flag must be evidence-based (cite specific data). Do not invent flags.

Return ONLY valid JSON in this exact format:
{{
  "green": [
    {{"label": "Strong Python expertise", "evidence": "5 public Python repos, 200+ stars", "weight": "high"}},
    ...
  ],
  "red": [
    {{"label": "Limited system design experience", "evidence": "No mentions of distributed systems in profile", "weight": "medium"}},
    ...
  ]
}}

Candidate Data:
{context}

JSON:"""

        raw = self._call_groq(prompt, max_tokens=800)
        try:
            # Strip markdown code blocks if present
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(cleaned)
            green = [CandidateFlag(**f) for f in data.get("green", [])[:5]]
            red = [CandidateFlag(**f) for f in data.get("red", [])[:5]]
            return {"green": green, "red": red}
        except Exception as exc:
            logger.warning("flags_parse_failed", error=str(exc), raw=raw[:200])
            return {
                "green": [CandidateFlag(label="See detailed analysis", evidence="LLM parsing error — check raw report", weight="low")],
                "red": [],
            }

    async def _generate_interview_questions(
        self, context: str, state: ResearchJobState
    ) -> list[str]:
        jd_context = f"Job Role: {state.input.jd_text[:300]}" if state.input.jd_text else "No JD provided"
        fit_context = ""
        if state.fit_score_data:
            missing = ", ".join(state.fit_score_data.breakdown.missing_skills[:5])
            fit_context = f"Skill gaps to probe: {missing}"

        prompt = f"""Generate exactly 10 tailored interview questions for this candidate.
Mix: 5 technical questions (specific to their stack and role), 3 behavioral questions, 2 culture/motivation questions.
Make questions specific to their profile — reference their actual projects, skills, and experience.

{jd_context}
{fit_context}

Candidate Summary:
{context[:1000]}

Return ONLY a JSON array of 10 strings:
["Question 1", "Question 2", ...]

JSON:"""

        raw = self._call_groq(prompt, max_tokens=600)
        try:
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            questions = json.loads(cleaned)
            if isinstance(questions, list):
                return [str(q) for q in questions[:10]]
        except Exception as exc:
            logger.warning("questions_parse_failed", error=str(exc))

        # Fallback: split by newline
        lines = [ln.strip().lstrip("0123456789.-) ") for ln in raw.split("\n") if ln.strip()]
        return [q for q in lines if len(q) > 10][:10]

    async def _generate_detailed_analysis(self, context: str) -> str:
        prompt = f"""Write a detailed 3-paragraph candidate analysis covering:
1. Technical depth and skill alignment
2. Career trajectory and growth signals
3. Potential concerns and how to address them in interview

Be professional, specific, and evidence-based. Avoid demographic bias.

{context}

Detailed Analysis:"""

        return self._call_groq(prompt, max_tokens=600)

    def _determine_suggested_role(self, state: ResearchJobState) -> str:
        if state.fit_score_data:
            return state.fit_score_data.role_fit
        if state.linkedin_data:
            return state.linkedin_data.current_role
        return "Role undetermined"

    def _call_groq(self, prompt: str, max_tokens: int = 500) -> str:
        """Synchronous Groq call with error handling."""
        try:
            response = self._groq.chat.completions.create(
                model=self._settings.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert technical recruiter and talent analyst. "
                            "Be objective, evidence-based, and bias-free. "
                            "Never mention demographic characteristics."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=self._settings.groq_temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("groq_call_failed", error=str(exc))
            return f"[Generation failed: {type(exc).__name__}]"