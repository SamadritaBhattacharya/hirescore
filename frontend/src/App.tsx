import { TopBar } from "@/components/TopBar";
import { IntroPanel } from "@/components/IntroPanel";
import { ResearchForm } from "@/components/form/ResearchForm";
import { ProgressView } from "@/components/pipeline/ProgressView";
import { ReportView } from "@/components/report/ReportView";
import { ErrorView } from "@/components/ErrorView";
import { useResearchJob } from "@/hooks/useResearchJob";

function App() {
  const { state, submit, reset } = useResearchJob();

  return (
    <div className="min-h-screen">
      <TopBar showReset={state.stage !== "form"} onReset={reset} />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        {state.stage === "form" && (
          <div className="space-y-5">
            <IntroPanel />
            <ResearchForm onSubmit={submit} submitting={state.submitting} />
          </div>
        )}

        {state.stage === "running" && (
          <ProgressView statuses={state.statuses} logs={state.logs} jobStatus={state.jobStatus} />
        )}

        {state.stage === "report" && state.report && (
          <ReportView report={state.report} onReset={reset} />
        )}

        {state.stage === "error" && (
          <ErrorView
            message={state.error ?? "An unexpected error occurred."}
            statuses={state.statuses}
            onRetry={reset}
          />
        )}
      </main>
      <footer className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <p className="text-center text-[12px] text-[var(--color-ink-faint)]">
          HireScope — autonomous recruiting research agent
        </p>
      </footer>
    </div>
  );
}

export default App;
