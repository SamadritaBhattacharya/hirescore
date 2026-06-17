import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import type { FullReport } from "@/types/api";

const INK = [243, 243, 241];
const FAINT = [101, 101, 106];

function lerpGray(t: number): string {
  const [r1, g1, b1] = INK;
  const [r2, g2, b2] = FAINT;
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

export function GithubActivityPanel({ report }: { report: FullReport }) {
  const hasGithub =
    report.github_repos > 0 || Object.keys(report.language_breakdown).length > 0;

  if (!hasGithub) return null;

  const entries = Object.entries(report.language_breakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const data = entries.map(([name, value]) => ({
    name,
    value: Math.round(value),
  }));
  const topLang = entries[0]?.[0];

  return (
    <Card>
      <CardHeader>
        <CardTitle>GitHub Activity</CardTitle>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-3 gap-3">
          <Stat value={report.github_repos} label="Repos" />
          <Stat value={report.github_stars} label="Stars" />
          <Stat value={report.recent_commits_90d} label="Commits / 90d" />
        </div>

        {data.length > 0 && (
          <div className="mt-5 flex items-center gap-5 border-t border-[var(--color-line-soft)] pt-4">
            <div style={{ width: 96, height: 96 }} className="shrink-0">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={28}
                    outerRadius={46}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {data.map((_, i) => (
                      <Cell key={i} fill={lerpGray(i / Math.max(data.length - 1, 1))} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-line)",
                      borderRadius: 10,
                      fontSize: 12,
                      color: "var(--color-ink)",
                    }}
                    formatter={(value: any, name: any) => [`${value}%`, `${name}`]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-1.5">
              {entries.map(([name, value], i) => (
                <div key={name} className="flex items-center gap-2 text-[12.5px]">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: lerpGray(i / Math.max(entries.length - 1, 1)) }}
                  />
                  <span className="text-[var(--color-ink-dim)]">{name}</span>
                  <span className="ml-auto font-mono text-[var(--color-ink-faint)] font-tnum">
                    {Math.round(value)}%
                  </span>
                </div>
              ))}
              {total < 100 && topLang && (
                <p className="pt-1 text-[11px] text-[var(--color-ink-faint)]">
                  Remaining usage spread across other languages.
                </p>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-line-soft)] bg-[var(--color-surface-2)] px-3 py-3">
      <div className="font-mono text-[20px] font-medium text-[var(--color-ink)] font-tnum">
        {value}
      </div>
      <div className="text-[11.5px] text-[var(--color-ink-faint)]">{label}</div>
    </div>
  );
}
