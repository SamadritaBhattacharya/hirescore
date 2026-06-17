import type { ReactNode } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { weightLabel } from "@/lib/format";
import type { CandidateFlag } from "@/types/api";

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M8.5 12.5l2 2 5-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" strokeDasharray="2.5 2.5" />
      <path d="M12 8v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="16" r="0.9" fill="currentColor" />
    </svg>
  );
}

function FlagList({
  flags,
  icon,
  emptyText,
}: {
  flags: CandidateFlag[];
  icon: ReactNode;
  emptyText: string;
}) {
  if (flags.length === 0) {
    return <p className="text-[12.5px] text-[var(--color-ink-faint)]">{emptyText}</p>;
  }
  return (
    <ul className="space-y-3">
      {flags.map((f, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-0.5 shrink-0 text-[var(--color-ink-dim)]">{icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[13.5px] font-medium text-[var(--color-ink)]">{f.label}</span>
              <Badge
                tone={f.weight === "high" ? "strong" : f.weight === "medium" ? "default" : "muted"}
                className="px-1.5 py-0.5 text-[10px]"
              >
                {weightLabel(f.weight)}
              </Badge>
            </div>
            <p className="mt-0.5 text-[12.5px] leading-relaxed text-[var(--color-ink-dim)]">
              {f.evidence}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function FlagsPanel({
  greenFlags,
  redFlags,
}: {
  greenFlags: CandidateFlag[];
  redFlags: CandidateFlag[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Signals</CardTitle>
      </CardHeader>
      <CardBody className="grid gap-6 sm:grid-cols-2">
        <div>
          <div className="mb-3 flex items-center gap-1.5 text-[12px] font-medium text-[var(--color-ink-dim)]">
            <CheckIcon /> Strengths
          </div>
          <FlagList flags={greenFlags} icon={<CheckIcon />} emptyText="No notable strengths surfaced." />
        </div>
        <div className="border-t border-[var(--color-line-soft)] pt-5 sm:border-t-0 sm:border-l sm:pl-6 sm:pt-0">
          <div className="mb-3 flex items-center gap-1.5 text-[12px] font-medium text-[var(--color-ink-dim)]">
            <AlertIcon /> Concerns
          </div>
          <FlagList flags={redFlags} icon={<AlertIcon />} emptyText="No notable concerns surfaced." />
        </div>
      </CardBody>
    </Card>
  );
}
