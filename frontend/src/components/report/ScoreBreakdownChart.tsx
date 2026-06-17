import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import type { ScoreBreakdown } from "@/types/api";

interface Props {
  breakdown: ScoreBreakdown;
}

export function ScoreBreakdownChart({ breakdown }: Props) {
  const data = [
    { label: "Skill match", value: round(breakdown.skill_match_score) },
    { label: "Experience match", value: round(breakdown.experience_match_score) },
    { label: "Project relevance", value: round(breakdown.project_relevance_score) },
    { label: "Activity", value: round(breakdown.activity_score) },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fit Breakdown</CardTitle>
        <span className="font-mono text-[12px] text-[var(--color-ink-faint)]">/ 100</span>
      </CardHeader>
      <CardBody>
        <div style={{ width: "100%", height: 196 }}>
          <ResponsiveContainer>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
              barCategoryGap={18}
            >
              <XAxis type="number" domain={[0, 100]} hide />
              <YAxis
                type="category"
                dataKey="label"
                width={130}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--color-ink-dim)", fontSize: 12.5 }}
              />
              <Tooltip
                cursor={{ fill: "var(--color-surface-2)" }}
                contentStyle={{
                  background: "var(--color-surface-2)",
                  border: "1px solid var(--color-line)",
                  borderRadius: 10,
                  fontSize: 12.5,
                  color: "var(--color-ink)",
                }}
                labelStyle={{ color: "var(--color-ink-dim)" }}
                formatter={(value: any) => [`${value}`, "Score"]}
              />
              <Bar
                dataKey="value"
                radius={[6, 6, 6, 6]}
                background={{ fill: "var(--color-line-soft)", radius: 6 }}
                maxBarSize={14}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill="var(--color-ink)" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        {breakdown.reasoning && (
          <p className="mt-2 border-t border-[var(--color-line-soft)] pt-3 text-[13px] leading-relaxed text-[var(--color-ink-dim)]">
            {breakdown.reasoning}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

function round(v: number) {
  return Math.round(v * 100);
}
