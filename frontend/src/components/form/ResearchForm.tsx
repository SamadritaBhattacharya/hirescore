import * as React from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Field, Input, Textarea } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/form/SegmentedControl";
import { FileDrop } from "@/components/form/FileDrop";
import { Button } from "@/components/ui/Button";
import { emptyResearchInput, type ResearchInputForm } from "@/types/api";

type LinkedInMode = "url" | "text";
type DocMode = "upload" | "text";

interface Props {
  onSubmit: (input: ResearchInputForm) => void;
  submitting: boolean;
}

export function ResearchForm({ onSubmit, submitting }: Props) {
  const [input, setInput] = React.useState<ResearchInputForm>(emptyResearchInput());
  const [linkedinMode, setLinkedinMode] = React.useState<LinkedInMode>("url");
  const [jdMode, setJdMode] = React.useState<DocMode>("upload");
  const [cultureMode, setCultureMode] = React.useState<DocMode>("upload");
  const [touched, setTouched] = React.useState(false);

  const set = <K extends keyof ResearchInputForm>(key: K, value: ResearchInputForm[K]) =>
    setInput((s) => ({ ...s, [key]: value }));

  const linkedinValid = input.linkedin_url.trim() !== "" || input.linkedin_text.trim() !== "";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!linkedinValid) return;
    onSubmit(input);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Candidate Source</CardTitle>
          <SegmentedControl
            value={linkedinMode}
            onChange={setLinkedinMode}
            options={[
              { label: "Profile URL", value: "url" },
              { label: "Paste text", value: "text" },
            ]}
          />
        </CardHeader>
        <CardBody className="space-y-4">
          {linkedinMode === "url" ? (
            <Field label="LinkedIn URL" required hint="The primary identifier the agent researches against.">
              <Input
                type="url"
                placeholder="https://linkedin.com/in/janedoe"
                value={input.linkedin_url}
                onChange={(e) => set("linkedin_url", e.target.value)}
              />
            </Field>
          ) : (
            <Field
              label="LinkedIn profile text"
              required
              hint="Use this if scraping is blocked — paste the profile content directly."
            >
              <Textarea
                rows={5}
                placeholder="Paste the candidate's LinkedIn profile content…"
                value={input.linkedin_text}
                onChange={(e) => set("linkedin_text", e.target.value)}
              />
            </Field>
          )}
          {touched && !linkedinValid && (
            <p className="text-[12.5px] text-[var(--color-ink-dim)]">
              Provide a LinkedIn URL or pasted profile text to continue.
            </p>
          )}
          <Field label="GitHub URL" hint="Optional — enables the GitHub research agent.">
            <Input
              type="url"
              placeholder="https://github.com/janedoe"
              value={input.github_url}
              onChange={(e) => set("github_url", e.target.value)}
            />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Job Context</CardTitle>
          <SegmentedControl
            value={jdMode}
            onChange={setJdMode}
            options={[
              { label: "Upload", value: "upload" },
              { label: "Paste text", value: "text" },
            ]}
          />
        </CardHeader>
        <CardBody className="space-y-4">
          {jdMode === "upload" ? (
            <FileDrop
              label="Job description"
              hint="PDF, DOCX, or TXT. Skip this for an open-ended fit assessment."
              file={input.jd_file}
              onChange={(f) => set("jd_file", f)}
              accept=".pdf,.docx,.doc,.txt"
            />
          ) : (
            <Field label="Job description" hint="Skip this for an open-ended fit assessment.">
              <Textarea
                rows={5}
                placeholder="Paste the job description…"
                value={input.jd_text}
                onChange={(e) => set("jd_text", e.target.value)}
              />
            </Field>
          )}
          <Field label="Extra context" hint="Anything else the agent should weigh — team, level, must-haves.">
            <Textarea
              rows={3}
              placeholder="e.g. Senior+ only, must have led a team, remote-first culture…"
              value={input.extra_context}
              onChange={(e) => set("extra_context", e.target.value)}
            />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <FileDrop
            label="Resume"
            hint="Used to corroborate and fill gaps in the LinkedIn profile."
            file={input.resume_file}
            onChange={(f) => set("resume_file", f)}
            accept=".pdf,.docx,.doc,.txt"
          />

          <div className="flex items-center justify-between">
            <span className="text-[13px] font-medium text-[var(--color-ink)]">
              Culture document
            </span>
            <SegmentedControl
              value={cultureMode}
              onChange={setCultureMode}
              options={[
                { label: "Upload", value: "upload" },
                { label: "Paste text", value: "text" },
              ]}
            />
          </div>
          {cultureMode === "upload" ? (
            <FileDrop
              label=""
              hint="Optional — improves the culture-fit score."
              file={input.culture_file}
              onChange={(f) => set("culture_file", f)}
              accept=".pdf,.docx,.doc,.txt"
            />
          ) : (
            <Textarea
              rows={4}
              placeholder="Paste values, principles, or team norms…"
              value={input.culture_text}
              onChange={(e) => set("culture_text", e.target.value)}
            />
          )}
        </CardBody>
      </Card>

      <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-[12.5px] text-[var(--color-ink-faint)]">
          Six agents run in sequence and in parallel — typically under a minute.
        </p>
        <Button type="submit" size="lg" loading={submitting} disabled={submitting} className="sm:self-auto">
          Run research
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 12h14M13 6l6 6-6 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Button>
      </div>
    </form>
  );
}
