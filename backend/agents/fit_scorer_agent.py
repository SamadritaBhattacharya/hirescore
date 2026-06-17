"""
Fit Scorer Agent.

Responsibilities:
- RAG over JD + Culture Doc + Resume using ChromaDB + sentence-transformers
- Mathematically compute bias-free Hire Score (no LLM guessing the number)
- LLM only explains the score reasoning
- In no-JD mode: score against role archetypes

Bias-Free Score Formula:
    Hire Score = skill_match(40%) + experience(25%) + project_relevance(20%) + activity(15%)
    All components are factual/measurable — LLM explains but never sets the number.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from groq import Groq
from sentence_transformers import SentenceTransformer

from core.config import get_settings
from core.logging import get_logger
from agents.base_agent import BaseAgent
from models.schemas import (
    AgentName,
    FitScoreResult,
    HireVerdict,
    ResearchJobState,
    RoleArchetype,
    ScoreBreakdown,
)

logger = get_logger(__name__)

# Role archetype skill profiles for no-JD mode
ROLE_ARCHETYPES: dict[RoleArchetype, list[str]] = {
    RoleArchetype.ML_ENGINEER: [
        "python", "pytorch", "tensorflow", "scikit-learn", "machine learning",
        "deep learning", "model training", "mlops", "hugging face", "llm",
        "docker", "kubernetes", "sql", "git",
    ],
    RoleArchetype.BACKEND_ENGINEER: [
        "python", "java", "node.js", "fastapi", "django", "rest api",
        "postgresql", "redis", "docker", "kubernetes", "aws", "sql", "git",
    ],
    RoleArchetype.DATA_SCIENTIST: [
        "python", "pandas", "numpy", "scikit-learn", "statistics",
        "machine learning", "sql", "tableau", "jupyter", "r", "matplotlib",
    ],
    RoleArchetype.DEVOPS_ENGINEER: [
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
        "ci/cd", "jenkins", "github actions", "linux", "bash", "python",
    ],
    RoleArchetype.FULLSTACK_ENGINEER: [
        "react", "javascript", "typescript", "node.js", "python",
        "sql", "rest api", "docker", "git", "css", "html",
    ],
}

VERDICT_THRESHOLDS = [
    (85, HireVerdict.STRONG_YES),
    (70, HireVerdict.YES),
    (50, HireVerdict.MAYBE),
    (35, HireVerdict.NO),
    (0, HireVerdict.STRONG_NO),
]


class FitScorerAgent(BaseAgent):
    """
    Computes a bias-free hire score using RAG + mathematical scoring.
    Embeddings run locally (sentence-transformers) — zero API cost.
    """

    _embedding_model: SentenceTransformer | None = None  # class-level cache

    def __init__(self) -> None:
        super().__init__(name=AgentName.FIT_SCORER, timeout_seconds=90)
        self._settings = get_settings()
        self._groq = Groq(api_key=self._settings.groq_api_key)
        self._chroma = chromadb.Client(
            ChromaSettings(
                persist_directory=self._settings.chroma_persist_path,
                anonymized_telemetry=False,
            )
        )

    @classmethod
    def _get_embedding_model(cls) -> SentenceTransformer:
        """Lazy-load and cache the embedding model (loaded once at class level)."""
        if cls._embedding_model is None:
            logger.info("loading_embedding_model")
            cls._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._embedding_model

    async def execute(self, state: ResearchJobState) -> ResearchJobState:
        loop = asyncio.get_event_loop()

        # Run embedding + scoring in executor (CPU-bound)
        result = await loop.run_in_executor(
            None, self._compute_fit, state
        )
        state.fit_score_data = result
        return state

    def _compute_fit(self, state: ResearchJobState) -> FitScoreResult:
        """Main scoring pipeline — runs synchronously in thread pool."""
        has_jd = bool(state.input.jd_text)

        # Extract candidate skills from all available sources
        candidate_skills = self._extract_candidate_skills(state)
        candidate_years = self._extract_experience_years(state)

        if has_jd:
            return self._score_with_jd(state, candidate_skills, candidate_years)
        else:
            return self._score_without_jd(state, candidate_skills, candidate_years)

    def _score_with_jd(
        self,
        state: ResearchJobState,
        candidate_skills: list[str],
        candidate_years: float,
    ) -> FitScoreResult:
        """Score against a specific JD using RAG."""
        jd_text = state.input.jd_text or ""

        # Extract JD requirements
        jd_skills = self._extract_skills_from_text(jd_text)
        required_years = self._extract_required_years(jd_text)

        # Build RAG context
        collection_name = f"job_{hash(jd_text[:100]) % 100000}"
        collection = self._build_rag_collection(
            collection_name=collection_name,
            documents={
                "jd": jd_text,
                "culture": state.input.culture_doc_text or "",
                "resume": state.input.resume_text or "",
            },
        )

        # Component 1: Skill Match (40%)
        skill_match, matched, missing, extra = self._compute_skill_match(
            candidate_skills, jd_skills
        )

        # Component 2: Experience Match (25%)
        exp_match = self._compute_experience_match(candidate_years, required_years)

        # Component 3: Project Relevance via RAG (20%)
        project_relevance = self._compute_project_relevance(
            collection=collection,
            candidate_text=self._build_candidate_text(state),
            jd_text=jd_text,
        )

        # Component 4: Activity Score (15%)
        activity_score = self._compute_activity_score(state)

        # Weighted hire score
        raw_score = (
            skill_match * 0.40
            + exp_match * 0.25
            + project_relevance * 0.20
            + activity_score * 0.15
        )
        hire_score = round(raw_score * 100)

        # Culture fit via RAG
        culture_score, culture_reasoning = self._compute_culture_fit(
            collection=collection,
            candidate_text=self._build_candidate_text(state),
        )

        # LLM explanation (never sets the number)
        reasoning = self._generate_score_reasoning(
            hire_score=hire_score,
            matched_skills=matched,
            missing_skills=missing,
            candidate_years=candidate_years,
            required_years=required_years,
            jd_text=jd_text,
        )

        breakdown = ScoreBreakdown(
            skill_match_score=skill_match,
            experience_match_score=exp_match,
            project_relevance_score=project_relevance,
            activity_score=activity_score,
            matched_skills=matched,
            missing_skills=missing,
            extra_skills=extra,
            skill_match_percentage=round(skill_match * 100, 1),
            experience_years_candidate=candidate_years,
            experience_years_required=required_years,
            reasoning=reasoning,
        )

        return FitScoreResult(
            hire_score=hire_score,
            hire_verdict=self._get_verdict(hire_score),
            role_fit="Specific role match based on JD",
            best_fit_archetype=self._guess_archetype(jd_skills),
            breakdown=breakdown,
            culture_fit_score=culture_score,
            culture_fit_reasoning=culture_reasoning,
            jd_mode=True,
        )

    def _score_without_jd(
        self,
        state: ResearchJobState,
        candidate_skills: list[str],
        candidate_years: float,
    ) -> FitScoreResult:
        """Score against role archetypes when no JD is given."""
        best_archetype = RoleArchetype.UNKNOWN
        best_score = 0.0
        best_matched: list[str] = []
        best_missing: list[str] = []

        for archetype, archetype_skills in ROLE_ARCHETYPES.items():
            skill_match, matched, missing, _ = self._compute_skill_match(
                candidate_skills, archetype_skills
            )
            if skill_match > best_score:
                best_score = skill_match
                best_archetype = archetype
                best_matched = matched
                best_missing = missing

        activity_score = self._compute_activity_score(state)
        exp_match = min(candidate_years / 3.0, 1.0)  # Normalize to 3 years baseline

        raw_score = best_score * 0.45 + exp_match * 0.30 + activity_score * 0.25
        hire_score = round(raw_score * 100)

        # Culture fit (no culture doc = neutral 50)
        culture_score = 50
        culture_reasoning = "No culture document provided — culture fit not evaluated."
        if state.input.culture_doc_text:
            collection = self._build_rag_collection(
                collection_name="culture_only",
                documents={"culture": state.input.culture_doc_text},
            )
            culture_score, culture_reasoning = self._compute_culture_fit(
                collection=collection,
                candidate_text=self._build_candidate_text(state),
            )

        reasoning = self._generate_score_reasoning(
            hire_score=hire_score,
            matched_skills=best_matched,
            missing_skills=best_missing,
            candidate_years=candidate_years,
            required_years=0,
            jd_text=f"No JD provided. Best archetype: {best_archetype.value}",
        )

        breakdown = ScoreBreakdown(
            skill_match_score=best_score,
            experience_match_score=exp_match,
            project_relevance_score=0.0,
            activity_score=activity_score,
            matched_skills=best_matched,
            missing_skills=best_missing,
            skill_match_percentage=round(best_score * 100, 1),
            experience_years_candidate=candidate_years,
            experience_years_required=0.0,
            reasoning=reasoning,
        )

        return FitScoreResult(
            hire_score=hire_score,
            hire_verdict=self._get_verdict(hire_score),
            role_fit=f"Best fit: {best_archetype.value}",
            best_fit_archetype=best_archetype,
            breakdown=breakdown,
            culture_fit_score=culture_score,
            culture_fit_reasoning=culture_reasoning,
            jd_mode=False,
        )

    # --- RAG helpers ---

    def _build_rag_collection(
        self,
        collection_name: str,
        documents: dict[str, str],
    ) -> Any:
        """Build or retrieve a ChromaDB collection from documents."""
        model = self._get_embedding_model()

        try:
            self._chroma.delete_collection(collection_name)
        except Exception:
            pass

        collection = self._chroma.create_collection(collection_name)
        ids, texts = [], []

        for doc_type, text in documents.items():
            if not text.strip():
                continue
            # Chunk into 500-char segments
            chunks = self._chunk_text(text, chunk_size=500, overlap=50)
            for i, chunk in enumerate(chunks):
                ids.append(f"{doc_type}_{i}")
                texts.append(chunk)

        if texts:
            embeddings = model.encode(texts, show_progress_bar=False).tolist()
            collection.add(ids=ids, embeddings=embeddings, documents=texts)

        return collection

    def _compute_project_relevance(
        self, collection: Any, candidate_text: str, jd_text: str
    ) -> float:
        """Query RAG with candidate profile against JD embedding."""
        if not candidate_text:
            return 0.5
        try:
            model = self._get_embedding_model()
            query_embedding = model.encode([candidate_text[:500]], show_progress_bar=False)[0].tolist()
            results = collection.query(
                query_embeddings=[query_embedding], n_results=min(3, collection.count())
            )
            distances = results.get("distances", [[]])[0]
            if not distances:
                return 0.5
            # Convert cosine distance to similarity
            avg_distance = sum(distances) / len(distances)
            return max(0.0, min(1.0, 1.0 - avg_distance))
        except Exception as exc:
            logger.warning("rag_query_failed", error=str(exc))
            return 0.5

    def _compute_culture_fit(
        self, collection: Any, candidate_text: str
    ) -> tuple[int, str]:
        """Use RAG to assess culture fit from culture doc."""
        if not candidate_text:
            return 50, "Insufficient data to assess culture fit."
        try:
            model = self._get_embedding_model()
            query_emb = model.encode([candidate_text[:500]], show_progress_bar=False)[0].tolist()
            results = collection.query(
                query_embeddings=[query_emb], n_results=min(3, collection.count())
            )
            distances = results.get("distances", [[]])[0]
            docs = results.get("documents", [[]])[0]
            if not distances:
                return 50, "No culture document indexed."
            similarity = max(0.0, min(1.0, 1.0 - (sum(distances) / len(distances))))
            score = round(similarity * 100)
            reasoning = self._explain_culture_fit(score, docs)
            return score, reasoning
        except Exception as exc:
            logger.warning("culture_fit_failed", error=str(exc))
            return 50, "Culture fit evaluation failed."

    # --- Scoring helpers ---

    def _compute_skill_match(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
    ) -> tuple[float, list[str], list[str], list[str]]:
        """
        Exact + fuzzy skill matching.
        Returns (score, matched, missing, extra).
        """
        if not required_skills:
            return 0.5, [], [], candidate_skills

        cand_lower = {s.lower() for s in candidate_skills}
        req_lower = [s.lower() for s in required_skills]

        matched = [s for s in req_lower if self._skill_matches(s, cand_lower)]
        missing = [s for s in req_lower if not self._skill_matches(s, cand_lower)]
        extra = [s for s in cand_lower if not any(self._skill_matches(r, {s}) for r in req_lower)]

        score = len(matched) / len(req_lower) if req_lower else 0.0
        return (
            round(score, 3),
            [required_skills[req_lower.index(m)] for m in matched if m in req_lower],
            [required_skills[req_lower.index(m)] for m in missing if m in req_lower],
            list(extra)[:10],
        )

    def _skill_matches(self, required: str, candidate_set: set[str]) -> bool:
        """Flexible skill matching: exact, substring, and common aliases."""
        ALIASES = {
            "ml": "machine learning", "ai": "artificial intelligence",
            "js": "javascript", "ts": "typescript", "py": "python",
            "k8s": "kubernetes", "tf": "tensorflow",
        }
        req = ALIASES.get(required, required)
        if req in candidate_set:
            return True
        # Substring match (e.g., "react" matches "react.js")
        return any(req in c or c in req for c in candidate_set)

    def _compute_experience_match(
        self, candidate_years: float, required_years: float
    ) -> float:
        if required_years <= 0:
            return 0.7  # No requirement stated — neutral
        ratio = candidate_years / required_years
        # Diminishing returns above requirement, penalty below
        if ratio >= 1.0:
            return min(1.0, 0.8 + (ratio - 1.0) * 0.1)
        return ratio * 0.8

    def _compute_activity_score(self, state: ResearchJobState) -> float:
        """Score based on GitHub activity + community signals."""
        score = 0.0

        if state.github_data:
            gh = state.github_data
            # Commits in last 90 days (max contribution at 30+)
            commit_score = min(gh.recent_commit_count_90d / 30.0, 1.0)
            # Stars received (max at 100)
            star_score = min(gh.total_stars / 100.0, 1.0)
            # AI/ML repos bonus
            ai_bonus = 0.2 if gh.has_ai_ml_repos else 0.0
            # OSS contributions
            oss_score = min(len(gh.open_source_contributions) / 5.0, 1.0)

            score = (commit_score * 0.4 + star_score * 0.3 + oss_score * 0.3)
            score = min(score + ai_bonus, 1.0)

        if state.web_research_data:
            web = state.web_research_data
            # Hackathons and community presence
            community_bonus = min(
                (len(web.hackathons) * 0.1 + len(web.talks) * 0.1 + len(web.articles) * 0.05),
                0.3,
            )
            score = min(score + community_bonus, 1.0)

        return round(score, 3)

    # --- Text extraction ---

    def _extract_candidate_skills(self, state: ResearchJobState) -> list[str]:
        """Aggregate skills from all available sources (deduplicated)."""
        skills: list[str] = []

        if state.linkedin_data:
            skills.extend(state.linkedin_data.skills)

        if state.github_data:
            skills.extend(state.github_data.top_languages)

        if state.input.resume_text:
            skills.extend(self._extract_skills_from_text(state.input.resume_text))

        # Deduplicate preserving order
        seen: set[str] = set()
        unique = []
        for s in skills:
            low = s.lower()
            if low not in seen:
                seen.add(low)
                unique.append(s)
        return unique

    def _extract_skills_from_text(self, text: str) -> list[str]:
        """Extract tech skills from any text block."""
        TECH_SKILLS = [
            "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "C#",
            "React", "Vue", "Angular", "Next.js", "Node.js", "FastAPI", "Django",
            "Flask", "Spring", "FastAPI", "GraphQL", "REST API", "gRPC",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
            "Docker", "Kubernetes", "Terraform", "AWS", "GCP", "Azure", "CI/CD",
            "GitHub Actions", "Jenkins", "PyTorch", "TensorFlow", "Keras",
            "Scikit-learn", "Pandas", "NumPy", "Hugging Face", "LangChain",
            "LangGraph", "RAG", "LLM", "GPT", "BERT", "Transformers",
            "ChromaDB", "Pinecone", "FAISS", "Weaviate", "MLflow", "Airflow",
            "Spark", "Kafka", "dbt", "Tableau", "Power BI", "SQL", "Git",
            "Linux", "Bash", "OpenAI", "Groq", "Anthropic",
        ]
        found = [
            skill for skill in TECH_SKILLS
            if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE)
        ]
        return found

    def _extract_experience_years(self, state: ResearchJobState) -> float:
        """Best estimate of candidate's total experience years."""
        if state.linkedin_data and state.linkedin_data.total_experience_years > 0:
            return state.linkedin_data.total_experience_years
        if state.input.resume_text:
            year_pattern = re.compile(r"\b(20\d{2}|19\d{2})\b")
            years = [int(y) for y in year_pattern.findall(state.input.resume_text)]
            if len(years) >= 2:
                return float(max(years) - min(years))
        return 0.0

    def _extract_required_years(self, jd_text: str) -> float:
        """Extract required experience years from JD text."""
        patterns = [
            r"(\d+)\+?\s+years?\s+(?:of\s+)?(?:experience|exp)",
            r"minimum\s+(?:of\s+)?(\d+)\s+years?",
        ]
        for pattern in patterns:
            match = re.search(pattern, jd_text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return 0.0

    def _extract_skills_from_jd(self, jd_text: str) -> list[str]:
        return self._extract_skills_from_text(jd_text)

    def _build_candidate_text(self, state: ResearchJobState) -> str:
        """Concatenate all candidate data into a single embedding-ready string."""
        parts: list[str] = []
        if state.linkedin_data:
            li = state.linkedin_data
            parts.append(f"{li.name} {li.headline} {li.summary}")
            parts.append(" ".join(li.skills))
        if state.github_data:
            gh = state.github_data
            parts.append(f"{gh.bio}")
            parts.append(" ".join(gh.top_languages))
        if state.input.resume_text:
            parts.append(state.input.resume_text[:1000])
        return " ".join(filter(None, parts))

    def _chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def _get_verdict(self, score: int) -> HireVerdict:
        for threshold, verdict in VERDICT_THRESHOLDS:
            if score >= threshold:
                return verdict
        return HireVerdict.STRONG_NO

    def _guess_archetype(self, jd_skills: list[str]) -> RoleArchetype:
        """Guess the role archetype from JD skills."""
        jd_lower = {s.lower() for s in jd_skills}
        best = RoleArchetype.UNKNOWN
        best_count = 0
        for archetype, arch_skills in ROLE_ARCHETYPES.items():
            count = sum(1 for s in arch_skills if s in jd_lower)
            if count > best_count:
                best_count = count
                best = archetype
        return best

    def _explain_culture_fit(self, score: int, docs: list[str]) -> str:
        """Generate a brief culture fit explanation via LLM."""
        context = " ".join(docs[:2])[:500]
        prompt = (
            f"Culture fit score: {score}/100. "
            f"Based on these culture values: {context}\n"
            f"Write 2 sentences explaining the culture fit score. Be specific and factual."
        )
        try:
            response = self._groq.chat.completions.create(
                model=self._settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception:
            return f"Culture fit score: {score}/100"

    def _generate_score_reasoning(
        self,
        hire_score: int,
        matched_skills: list[str],
        missing_skills: list[str],
        candidate_years: float,
        required_years: float,
        jd_text: str,
    ) -> str:
        """LLM explains the score — it does NOT set it."""
        prompt = f"""You are an objective talent analyst. Explain the hire score.

Hire Score: {hire_score}/100
Matched Skills: {', '.join(matched_skills[:8]) or 'None identified'}
Missing Skills: {', '.join(missing_skills[:8]) or 'None'}
Candidate Experience: {candidate_years} years
Required Experience: {required_years} years
Role Context: {jd_text[:300]}

Write 3-4 sentences explaining WHY the score is {hire_score}. 
Be specific about the skill matches and gaps. Do not suggest changing the score.
Do not mention gender, age, location, or any demographic factors."""

        try:
            response = self._groq.chat.completions.create(
                model=self._settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("score_reasoning_failed", error=str(exc))
            return f"Hire score {hire_score}/100 based on skill and experience analysis."