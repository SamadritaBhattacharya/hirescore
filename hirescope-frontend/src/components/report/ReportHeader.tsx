import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ScoreRing } from "@/components/report/ScoreRing";
import { initials } from "@/lib/format";
import type { FullReport, HireVerdict } from "@/types/api";

const VERDICT_VISUAL: Record<
  HireVerdict,
  { tone: "strong" | "outline" | "default" | "muted"; arrow: string }
> = {
  "Strong Yes": { tone: "strong", arrow: "↑↑" },
  Yes: { tone: "outline", arrow: "↑" },
  Maybe: { tone: "default", arrow: "→" },
  No: { tone: "muted", arrow: "↓" },
  "Strong No": { tone: "muted", arrow: "↓↓" },
};

interface Props {
  report: FullReport;
  onExport: () => void;
  exporting: boolean;
  onReset: () => void;
}

export function ReportHeader({ report, onExport, exporting, onReset }: Props) {
  const visual = VERDICT_VISUAL[report.hire_verdict];
  const name = report.candidate_name || "Unnamed candidate";

  return (
    <Card className="p-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-full border border-[var(--color-line-strong)] bg-[var(--color-surface-2)] font-mono text-[14px] font-medium text-[var(--color-ink)]">
            {initials(name)}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-lg font-semibold text-[var(--color-ink)]">{name}</h1>
              <Badge tone={visual.tone}>
                {visual.arrow} {report.hire_verdict}
              </Badge>
            </div>
            <p className="mt-0.5 truncate text-[13.5px] text-[var(--color-ink-dim)]">
              {report.candidate_headline || report.candidate_current_role || "No headline available"}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {report.candidate_location && (
                <Badge tone="muted">{report.candidate_location}</Badge>
              )}
              {report.role_fit && <Badge tone="muted">{report.role_fit}</Badge>}
              {report.best_fit_archetype !== "Unknown" && (
                <Badge tone="muted">{report.best_fit_archetype}</Badge>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 self-stretch sm:self-auto">
          <div className="hidden h-12 w-px bg-[var(--color-line)] sm:block" />
          <ScoreRing value={report.hire_score} label="Hire score" />
          <div className="flex flex-col gap-2">
            <Button variant="secondary" size="sm" onClick={onExport} loading={exporting}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 16V4m0 12l-4-4m4 4l4-4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Export PDF
            </Button>
            <Button variant="ghost" size="sm" onClick={onReset}>
              New research
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
