import { Card } from "@/components/ui/Card";
import { PipelineRail, idleStatusMap } from "@/components/pipeline/PipelineRail";

export function IntroPanel() {
  return (
    <Card className="overflow-hidden px-6 pt-7 pb-4">
      <div className="mb-6 max-w-lg">
        <h1 className="text-xl font-semibold tracking-tight text-[var(--color-ink)]">
          New candidate research
        </h1>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--color-ink-dim)]">
          Six agents run in parallel and in sequence to research, score, and write up a
          candidate — routing the right sources, scoring fit against your role, then
          synthesizing a verdict with evidence.
        </p>
      </div>
      <PipelineRail statuses={idleStatusMap} className="max-w-3xl" />
    </Card>
  );
}
