import type { AgentName, FlagWeight, HireVerdict } from "@/types/api";

export function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

export function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

export const AGENT_LABELS: Record<AgentName, string> = {
  routing: "Routing",
  linkedin: "LinkedIn",
  github: "GitHub",
  web_research: "Web Research",
  fit_scorer: "Fit Scorer",
  synthesizer: "Synthesizer",
};

export const VERDICT_ORDER: HireVerdict[] = [
  "Strong No",
  "No",
  "Maybe",
  "Yes",
  "Strong Yes",
];

export function verdictStrength(v: HireVerdict): number {
  return VERDICT_ORDER.indexOf(v);
}

export function weightLabel(w: FlagWeight): string {
  return w.charAt(0).toUpperCase() + w.slice(1);
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
