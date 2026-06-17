import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";

export function InterviewQuestions({ questions }: { questions: string[] }) {
  if (questions.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Suggested Interview Questions</CardTitle>
      </CardHeader>
      <CardBody>
        <ol className="space-y-3">
          {questions.map((q, i) => (
            <li key={i} className="flex gap-3">
              <span className="font-mono text-[12px] text-[var(--color-ink-faint)] font-tnum pt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="text-[13.5px] leading-relaxed text-[var(--color-ink)]">{q}</span>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}
