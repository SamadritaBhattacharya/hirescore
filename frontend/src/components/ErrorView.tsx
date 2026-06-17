import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { PipelineRail, type StatusMap } from "@/components/pipeline/PipelineRail";

export function ErrorView({
  message,
  statuses,
  onRetry,
}: {
  message: string;
  statuses: StatusMap;
  onRetry: () => void;
}) {
  return (
    <div className="space-y-5">
      <Card className="px-6 pt-8">
        <PipelineRail statuses={statuses} className="max-w-3xl mx-auto" />
      </Card>
      <Card>
        <CardBody className="flex flex-col items-start gap-4 py-6">
          <div>
            <h2 className="text-[15px] font-semibold text-[var(--color-ink)]">
              Something went wrong
            </h2>
            <p className="mt-1 text-[13.5px] leading-relaxed text-[var(--color-ink-dim)]">
              {message}
            </p>
          </div>
          <Button variant="secondary" onClick={onRetry}>
            Start a new research job
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
