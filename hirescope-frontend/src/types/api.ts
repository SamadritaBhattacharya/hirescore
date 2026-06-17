/**
 * Types mirroring backend/models/schemas.py
 * Kept in lockstep with the FastAPI Pydantic models so the frontend
 * never has to guess at shapes coming back from the pipeline.
 */

export type JobStatus =
  | "pending"
  | "routing"
  | "researching"
  | "scoring"
  | "synthesizing"
  | "completed"
  | "failed";

export type AgentName =
  | "routing"
  | "linkedin"
  | "github"
  | "web_research"
  | "fit_scorer"
  | "synthesizer";

export type RoleArchetype =
  | "ML Engineer"
  | "Backend Engineer"
  | "Frontend Engineer"
  | "Full Stack Engineer"
  | "Data Scientist"
  | "Data Engineer"
  | "DevOps / MLOps Engineer"
  | "Product Manager"
  | "Research Scientist"
  | "Unknown";

export type HireVerdict = "Strong Yes" | "Yes" | "Maybe" | "No" | "Strong No";

export type FlagWeight = "high" | "medium" | "low";

export interface CandidateFlag {
  label: string;
  evidence: string;
  weight: FlagWeight;
}

export interface ScoreBreakdown {
  skill_match_score: number;
  experience_match_score: number;
  project_relevance_score: number;
  activity_score: number;
  matched_skills: string[];
  missing_skills: string[];
  extra_skills: string[];
  skill_match_percentage: number;
  experience_years_candidate: number;
  experience_years_required: number;
  reasoning: string;
}

export interface ResearchJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface FullReport {
  job_id: string;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;

  candidate_name: string;
  candidate_headline: string;
  candidate_location: string;
  candidate_current_role: string;

  executive_summary: string;
  hire_score: number;
  hire_verdict: HireVerdict;
  score_breakdown: ScoreBreakdown | null;
  culture_fit_score: number;
  culture_fit_reasoning: string;

  green_flags: CandidateFlag[];
  red_flags: CandidateFlag[];

  suggested_role: string;
  role_fit: string;
  best_fit_archetype: RoleArchetype;

  matched_skills: string[];
  missing_skills: string[];
  extra_skills: string[];
  top_languages: string[];
  language_breakdown: Record<string, number>;

  github_stars: number;
  github_repos: number;
  recent_commits_90d: number;
  hackathons: Record<string, string>[];
  community_signals: string[];

  interview_questions: string[];

  detailed_analysis: string;
  errors: Record<string, string>;
}

export interface ProgressEventPayload {
  agent: AgentName;
  status: "started" | "completed" | "failed";
  message: string;
  job_status: JobStatus;
}

export interface CompletedEventPayload {
  job_status: JobStatus;
  job_id?: string;
}

/** Input fields for starting a research job (multipart/form-data on the wire). */
export interface ResearchInputForm {
  linkedin_url: string;
  linkedin_text: string;
  github_url: string;
  jd_text: string;
  culture_text: string;
  extra_context: string;
  resume_file: File | null;
  jd_file: File | null;
  culture_file: File | null;
}

export const emptyResearchInput = (): ResearchInputForm => ({
  linkedin_url: "",
  linkedin_text: "",
  github_url: "",
  jd_text: "",
  culture_text: "",
  extra_context: "",
  resume_file: null,
  jd_file: null,
  culture_file: null,
});
