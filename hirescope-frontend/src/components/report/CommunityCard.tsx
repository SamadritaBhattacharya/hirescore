import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { FullReport } from "@/types/api";

export function CommunityCard({ report }: { report: FullReport }) {
  const hasHackathons = report.hackathons.length > 0;
  const hasSignals = report.community_signals.length > 0;
  if (!hasHackathons && !hasSignals) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Community & Recognition</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        {hasSignals && (
          <div className="flex flex-wrap gap-1.5">
            {report.community_signals.map((s, i) => (
              <Badge key={i} tone="default">
                {s}
              </Badge>
            ))}
          </div>
        )}
        {hasHackathons && (
          <ul className="space-y-2">
            {report.hackathons.map((h, i) => (
              <li
                key={i}
                className="flex items-center justify-between gap-3 rounded-xl border border-[var(--color-line-soft)] bg-[var(--color-surface-2)] px-3.5 py-2.5"
              >
                <span className="truncate text-[13px] text-[var(--color-ink)]">
                  {h.name || h.title || "Hackathon"}
                </span>
                {h.result && (
                  <span className="shrink-0 font-mono text-[12px] text-[var(--color-ink-dim)]">
                    {h.result}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
