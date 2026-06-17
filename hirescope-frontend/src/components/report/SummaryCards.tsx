import * as React from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";

export function SummaryCard({ summary }: { summary: string }) {
  if (!summary) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Executive Summary</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="text-[14px] leading-relaxed text-[var(--color-ink)]">{summary}</p>
      </CardBody>
    </Card>
  );
}

export function DetailedAnalysisCard({ analysis }: { analysis: string }) {
  const [open, setOpen] = React.useState(false);
  if (!analysis) return null;

  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4"
      >
        <span className="text-[13px] font-medium uppercase tracking-[0.06em] text-[var(--color-ink-dim)]">
          Detailed Analysis
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          className={`shrink-0 text-[var(--color-ink-faint)] transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="border-t border-[var(--color-line-soft)] px-5 py-4">
          <p className="whitespace-pre-line text-[13.5px] leading-relaxed text-[var(--color-ink-dim)]">
            {analysis}
          </p>
        </div>
      )}
    </Card>
  );
}
