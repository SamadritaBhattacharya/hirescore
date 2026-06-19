import type {
  FullReport,
  ResearchInputForm,
  ResearchJobResponse,
} from "@/types/api";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

/** Starts a new research job. Returns immediately with a job_id; the pipeline runs in the background. */
export async function startResearch(
  input: ResearchInputForm
): Promise<ResearchJobResponse> {
  const fd = new FormData();

  if (input.linkedin_url.trim()) fd.append("linkedin_url", input.linkedin_url.trim());
  if (input.linkedin_text.trim()) fd.append("linkedin_text", input.linkedin_text.trim());
  if (input.github_url.trim()) fd.append("github_url", input.github_url.trim());
  if (input.jd_text.trim()) fd.append("jd_text", input.jd_text.trim());
  if (input.culture_text.trim()) fd.append("culture_text", input.culture_text.trim());
  if (input.extra_context.trim()) fd.append("extra_context", input.extra_context.trim());
  if (input.resume_file) fd.append("resume_file", input.resume_file);
  if (input.jd_file) fd.append("jd_file", input.jd_file);
  if (input.culture_file) fd.append("culture_file", input.culture_file);

  const res = await fetch(`${API_BASE}/research/start`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new ApiError(detail ?? "Could not start research job.", res.status);
  }

  return res.json();
}

export async function getReport(jobId: string): Promise<FullReport> {
  const res = await fetch(`${API_BASE}/report/${jobId}`);
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new ApiError(detail ?? "Could not load report.", res.status);
  }
  return res.json();
}

export function exportReportUrl(jobId: string): string {
  return `${API_BASE}/report/${jobId}/export`;
}

export async function downloadReportPdf(jobId: string, candidateName: string) {
  const res = await fetch(exportReportUrl(jobId), { method: "POST" });

  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new ApiError(detail ?? `Could not export PDF (status ${res.status}).`, res.status);
  }

  // The export endpoint can return 200 with a non-PDF body in edge cases
  // (e.g. a misconfigured proxy returning an HTML error page). Guard against
  // silently "succeeding" and downloading a corrupt file.
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/pdf")) {
    const detail = await safeDetail(res);
    throw new ApiError(
      detail ?? "The server did not return a PDF. The export may have failed silently.",
      res.status
    );
  }

  const blob = await res.blob();
  if (blob.size === 0) {
    throw new ApiError("The exported PDF was empty.", res.status);
  }

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  const safeName = candidateName.trim().replace(/\s+/g, "_") || "candidate";
  a.href = url;
  a.download = `HireScope_${safeName}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

async function safeDetail(res: Response): Promise<string | null> {
  try {
    const body = await res.json();
    return body?.detail ?? null;
  } catch {
    return null;
  }
}

/**
 * Opens the SSE progress stream for a job.
 * Returns a cleanup function to close the connection.
 *
 * Uses raw fetch + ReadableStream parsing rather than EventSource because
 * EventSource cannot be cancelled/cleaned up as predictably across browsers
 * and we want a single code path for both proxied dev and same-origin prod.
 */
export function streamProgress(
  jobId: string,
  handlers: {
    onEvent: (eventType: string, data: unknown) => void;
    onError?: (err: Error) => void;
  }
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/research/${jobId}/stream`, {
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`Stream failed with status ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          let eventType = "message";
          let data = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) eventType = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (data) {
            try {
              handlers.onEvent(eventType, JSON.parse(data));
            } catch {
              // ignore malformed frame
            }
          }
        }
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return () => controller.abort();
}