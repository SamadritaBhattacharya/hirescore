"""
HireScope FastAPI Application.

Endpoints:
  POST /api/v1/research/start     — Start a research job
  GET  /api/v1/research/{job_id}/stream — SSE progress stream
  GET  /api/v1/report/{job_id}    — Get completed report
  POST /api/v1/report/{job_id}/export — Download PDF
  GET  /api/v1/health             — Health check
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from core.config import Settings, get_settings
from exporters.job_store import JobStore, get_job_store
from core.logging import configure_logging, get_logger
from parsers.report_builder import ReportBuilder
from exporters.pdf_exporter import PDFExporter
from orchestrator.orchestrator import HireScopeOrchestrator
from models.schemas import (
    FullReport,
    JobStatus,
    ResearchInput,
    ResearchJobResponse,
    ResearchJobState,
)
from parsers.document_parser import DocumentParserFactory

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    configure_logging()
    logger.info("hirescope_startup")
    yield
    logger.info("hirescope_shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HireScope API",
        description="Autonomous Recruiting Research Agent",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_orchestrator() -> HireScopeOrchestrator:
    return HireScopeOrchestrator()


def get_pdf_exporter() -> PDFExporter:
    return PDFExporter()


def get_report_builder() -> ReportBuilder:
    return ReportBuilder()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def parse_upload(file: UploadFile | None) -> str:
    """Read and parse an uploaded file to text. Returns empty string if None."""
    if file is None or not file.filename:
        return ""
    content = await file.read()
    if not content:
        return ""
    return DocumentParserFactory.parse(content, file.filename)


async def run_research_job(
    job_id: UUID,
    state: ResearchJobState,
    store: JobStore,
    orchestrator: HireScopeOrchestrator,
) -> None:
    """Background task: run the full pipeline and update job store."""
    try:
        updated_state = await orchestrator.run(state)
        await store.update(updated_state)
    except Exception as exc:
        logger.exception("research_job_failed", job_id=str(job_id), error=str(exc))
        state.status = JobStatus.FAILED
        state.errors["pipeline"] = str(exc)
        await store.update(state)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "env": settings.app_env,
        "groq_model": settings.groq_model,
    }


@app.post("/api/v1/research/start", response_model=ResearchJobResponse, status_code=202)
async def start_research(
    background_tasks: BackgroundTasks,
    # Required: at least one of these
    linkedin_url: str | None = Form(default=None),
    linkedin_text: str | None = Form(default=None),
    # Optional URLs
    github_url: str | None = Form(default=None),
    # Optional text fields
    extra_context: str | None = Form(default=None),
    # Optional file uploads
    resume_file: UploadFile | None = File(default=None),
    jd_file: UploadFile | None = File(default=None),
    culture_file: UploadFile | None = File(default=None),
    # JD / culture as text alternative
    jd_text: str | None = Form(default=None),
    culture_text: str | None = Form(default=None),
    # Dependencies
    store: JobStore = Depends(get_job_store),
    orchestrator: HireScopeOrchestrator = Depends(get_orchestrator),
) -> ResearchJobResponse:
    """
    Start an autonomous research job.
    Accepts multipart/form-data with optional file uploads.
    Returns job_id immediately; research runs in background.
    """
    # Parse uploaded documents
    resume_text = await parse_upload(resume_file)
    parsed_jd = await parse_upload(jd_file)
    parsed_culture = await parse_upload(culture_file)

    # Merge file + text inputs (file takes precedence)
    final_jd = parsed_jd or jd_text or None
    final_culture = parsed_culture or culture_text or None

    try:
        research_input = ResearchInput(
            linkedin_url=linkedin_url or None,
            linkedin_text=linkedin_text or None,
            github_url=github_url or None,
            resume_text=resume_text or None,
            jd_text=final_jd,
            culture_doc_text=final_culture,
            extra_context=extra_context or None,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    state = ResearchJobState(input=research_input)
    await store.create(state)

    background_tasks.add_task(
        run_research_job,
        job_id=state.job_id,
        state=state,
        store=store,
        orchestrator=orchestrator,
    )

    logger.info("research_job_queued", job_id=str(state.job_id))

    return ResearchJobResponse(job_id=state.job_id, status=state.status)


@app.get("/api/v1/research/{job_id}/stream")
async def stream_progress(
    job_id: UUID,
    store: JobStore = Depends(get_job_store),
) -> StreamingResponse:
    """
    SSE endpoint. Streams progress events until job is complete or failed.
    Frontend connects here to show real-time progress.
    """
    state = await store.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = await store.subscribe(job_id)

        try:
            # Send any already-emitted events first
            current = await store.get(job_id)
            if current:
                for event in current.progress_events:
                    yield _format_sse("progress", {
                        "agent": event.agent.value,
                        "status": event.status,
                        "message": event.message,
                        "job_status": current.status.value,
                    })

                if current.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    yield _format_sse("completed", {"job_status": current.status.value})
                    return

            # Stream live updates
            while True:
                try:
                    updated: ResearchJobState = await asyncio.wait_for(
                        queue.get(), timeout=30.0
                    )
                    # Emit new progress events
                    for event in updated.progress_events[-3:]:  # send last few
                        yield _format_sse("progress", {
                            "agent": event.agent.value,
                            "status": event.status,
                            "message": event.message,
                            "job_status": updated.status.value,
                        })

                    if updated.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                        yield _format_sse("completed", {
                            "job_status": updated.status.value,
                            "job_id": str(job_id),
                        })
                        break

                except asyncio.TimeoutError:
                    yield _format_sse("ping", {"alive": True})

        finally:
            await store.unsubscribe(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/v1/report/{job_id}", response_model=FullReport)
async def get_report(
    job_id: UUID,
    store: JobStore = Depends(get_job_store),
) -> FullReport:
    """Retrieve the completed research report."""
    state = await store.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    if state.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail="Research job failed")
    if state.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=202, detail="Research still in progress")

    return ReportBuilder.build(state)


@app.post("/api/v1/report/{job_id}/export")
async def export_pdf(
    job_id: UUID,
    store: JobStore = Depends(get_job_store),
    exporter: PDFExporter = Depends(get_pdf_exporter),
) -> Response:
    """Generate and return PDF report for download."""
    state = await store.get(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    if state.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Report not ready yet")

    report = ReportBuilder.build(state)

    try:
        pdf_bytes = await exporter.export(report)
    except Exception as exc:
        logger.error("pdf_export_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(status_code=500, detail="PDF generation failed")

    candidate_name = report.candidate_name.replace(" ", "_") or "candidate"
    filename = f"HireScope_{candidate_name}_{job_id.hex[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# SSE formatter
# ---------------------------------------------------------------------------


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)