import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ScoreRing } from "@/components/report/ScoreRing";
import type { FullReport } from "@/types/api";

export function CultureFitCard({ report }: { report: FullReport }) {
  const b = report.score_breakdown;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Culture Fit</CardTitle>
      </CardHeader>
      <CardBody>
        <div className="flex items-center gap-5">
          <ScoreRing value={report.culture_fit_score} size={92} strokeWidth={6} />
          <p className="text-[13px] leading-relaxed text-[var(--color-ink-dim)]">
            {report.culture_fit_reasoning || "No culture document was supplied, so this score reflects general signal only."}
          </p>
        </div>

        {b && (b.experience_years_candidate > 0 || b.experience_years_required > 0) && (
          <div className="mt-5 grid grid-cols-2 gap-3 border-t border-[var(--color-line-soft)] pt-4">
            <Stat label="Candidate experience" value={`${b.experience_years_candidate.toFixed(1)}y`} />
            <Stat label="Role requires" value={`${b.experience_years_required.toFixed(1)}y`} />
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[20px] font-medium text-[var(--color-ink)] font-tnum">
        {value}
      </div>
      <div className="text-[11.5px] text-[var(--color-ink-faint)]">{label}</div>
    </div>
  );
}
