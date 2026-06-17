import type { ReactNode } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ScoreBreakdown } from "@/types/api";

export function SkillsPanel({ breakdown }: { breakdown: ScoreBreakdown }) {
  const hasAny =
    breakdown.matched_skills.length ||
    breakdown.missing_skills.length ||
    breakdown.extra_skills.length;

  if (!hasAny) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Skills</CardTitle>
        <span className="font-mono text-[12px] text-[var(--color-ink-faint)]">
          {Math.round(breakdown.skill_match_percentage)}% match
        </span>
      </CardHeader>
      <CardBody className="grid gap-5 sm:grid-cols-3">
        <SkillGroup
          title="Matched"
          skills={breakdown.matched_skills}
          render={(s) => (
            <Badge key={s} tone="strong">
              {s}
            </Badge>
          )}
        />
        <SkillGroup
          title="Missing"
          skills={breakdown.missing_skills}
          render={(s) => (
            <Badge key={s} tone="muted" className="border-dashed">
              {s}
            </Badge>
          )}
        />
        <SkillGroup
          title="Beyond the role"
          skills={breakdown.extra_skills}
          render={(s) => (
            <Badge key={s} tone="outline">
              {s}
            </Badge>
          )}
        />
      </CardBody>
    </Card>
  );
}

function SkillGroup({
  title,
  skills,
  render,
}: {
  title: string;
  skills: string[];
  render: (s: string) => ReactNode;
}) {
  return (
    <div>
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-[12px] font-medium text-[var(--color-ink-dim)]">{title}</span>
        <span className="font-mono text-[11px] text-[var(--color-ink-faint)]">{skills.length}</span>
      </div>
      {skills.length === 0 ? (
        <p className="text-[12.5px] text-[var(--color-ink-faint)]">None</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">{skills.map(render)}</div>
      )}
    </div>
  );
}
