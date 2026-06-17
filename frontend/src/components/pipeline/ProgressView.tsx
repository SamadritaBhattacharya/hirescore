import * as React from "react";
import { Card } from "@/components/ui/Card";
import { PipelineRail, type StatusMap } from "@/components/pipeline/PipelineRail";
import { AGENT_LABELS } from "@/lib/format";
import type { JobStatus, ProgressEventPayload } from "@/types/api";

const STATUS_COPY: Record<JobStatus, string> = {
  pending: "Queued",
  routing: "Deciding which agents to run",
  researching: "Gathering candidate signal",
  scoring: "Scoring fit against the role",
  synthesizing: "Writing the final assessment",
  completed: "Complete",
  failed: "Failed",
};

export function ProgressView({
  statuses,
  logs,
  jobStatus,
}: {
  statuses: StatusMap;
  logs: ProgressEventPayload[];
  jobStatus: JobStatus;
}) {
  const logRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="space-y-5">
      <Card className="px-6 py-10">
        <div className="mb-8 text-center">
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3 py-1 text-[12px] font-mono text-[var(--color-ink-dim)]">
            <span className="relative flex size-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-[var(--color-ink-dim)] opacity-60" />
              <span className="relative size-1.5 rounded-full bg-[var(--color-ink)]" />
            </span>
            {jobStatus.toUpperCase()}
          </div>
          <h2 className="text-xl font-semibold text-[var(--color-ink)]">
            {STATUS_COPY[jobStatus]}
          </h2>
        </div>
        <PipelineRail statuses={statuses} className="max-w-3xl mx-auto" />
      </Card>

      <Card>
        <div className="flex items-center justify-between border-b border-[var(--color-line-soft)] px-5 py-3">
          <span className="text-[13px] font-medium uppercase tracking-[0.06em] text-[var(--color-ink-dim)]">
            Activity log
          </span>
          <span className="font-mono text-[12px] text-[var(--color-ink-faint)]">
            {logs.length} event{logs.length === 1 ? "" : "s"}
          </span>
        </div>
        <div
          ref={logRef}
          className="max-h-72 overflow-y-auto px-5 py-4 font-mono text-[12.5px] leading-relaxed"
        >
          {logs.length === 0 ? (
            <p className="text-[var(--color-ink-faint)]">Waiting for the pipeline to start…</p>
          ) : (
            logs.map((log, i) => (
              <div
                key={i}
                className="flex gap-2 animate-fade-up text-[var(--color-ink-dim)]"
              >
                <span className="text-[var(--color-ink-faint)]">{">"}</span>
                <span className="text-[var(--color-ink)]">{AGENT_LABELS[log.agent]}</span>
                <span className="text-[var(--color-ink-faint)]">
                  {log.status}
                  {log.message ? ` — ${log.message}` : ""}
                </span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
