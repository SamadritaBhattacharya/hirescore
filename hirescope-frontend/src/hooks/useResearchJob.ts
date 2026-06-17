import * as React from "react";
import { getReport, startResearch, streamProgress, ApiError } from "@/lib/api";
import { idleStatusMap, type StatusMap } from "@/components/pipeline/PipelineRail";
import type {
  AgentName,
  FullReport,
  JobStatus,
  ProgressEventPayload,
  ResearchInputForm,
} from "@/types/api";

export type Stage = "form" | "running" | "report" | "error";

interface State {
  stage: Stage;
  jobId: string | null;
  statuses: StatusMap;
  logs: ProgressEventPayload[];
  jobStatus: JobStatus;
  report: FullReport | null;
  error: string | null;
  submitting: boolean;
}

const initialState: State = {
  stage: "form",
  jobId: null,
  statuses: idleStatusMap,
  logs: [],
  jobStatus: "pending",
  report: null,
  error: null,
  submitting: false,
};

function applyProgress(statuses: StatusMap, event: ProgressEventPayload): StatusMap {
  const next = { ...statuses };
  const agent = event.agent as AgentName;
  if (event.status === "started") next[agent] = "active";
  else if (event.status === "completed") next[agent] = "done";
  else if (event.status === "failed") next[agent] = "failed";
  return next;
}

export function useResearchJob() {
  const [state, setState] = React.useState<State>(initialState);
  const stopRef = React.useRef<(() => void) | null>(null);

  const reset = React.useCallback(() => {
    stopRef.current?.();
    setState(initialState);
  }, []);

  const submit = React.useCallback(async (input: ResearchInputForm) => {
    setState((s) => ({ ...s, submitting: true, error: null }));
    try {
      const res = await startResearch(input);
      setState({
        ...initialState,
        stage: "running",
        jobId: res.job_id,
        jobStatus: res.status,
        submitting: false,
      });

      const stop = streamProgress(res.job_id, {
        onEvent: (eventType, data) => {
          if (eventType === "progress") {
            const payload = data as ProgressEventPayload;
            setState((s) => ({
              ...s,
              statuses: applyProgress(s.statuses, payload),
              logs: [...s.logs, payload],
              jobStatus: payload.job_status,
            }));
          } else if (eventType === "completed") {
            setState((s) => ({ ...s, jobStatus: data.job_status }));
            void finalize(res.job_id, data.job_status as JobStatus);
          }
        },
        onError: () => {
          setState((s) => ({
            ...s,
            stage: "error",
            error: "Lost connection to the research stream. The job may still be running.",
          }));
        },
      });
      stopRef.current = stop;
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not start the research job.";
      setState((s) => ({ ...s, submitting: false, stage: "error", error: message }));
    }
  }, []);

  const finalize = React.useCallback(async (jobId: string, jobStatus: JobStatus) => {
    stopRef.current?.();
    if (jobStatus === "failed") {
      setState((s) => ({
        ...s,
        stage: "error",
        error: "The research pipeline failed. Check the log below for details.",
      }));
      return;
    }
    try {
      const report = await getReport(jobId);
      setState((s) => ({ ...s, stage: "report", report }));
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not load the finished report.";
      setState((s) => ({ ...s, stage: "error", error: message }));
    }
  }, []);

  React.useEffect(() => {
    return () => stopRef.current?.();
  }, []);

  return { state, submit, reset };
}
