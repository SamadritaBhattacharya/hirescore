# HireScope — Frontend

A React + Vite + TypeScript + Tailwind CSS frontend for the HireScope autonomous
recruiting research agent. Built against the FastAPI backend in `backend/`
(`main.py`, `models/schemas.py`).

## Stack

- React 19 + TypeScript, Vite 8
- Tailwind CSS v4 (via `@tailwindcss/vite`, no separate config file — theme tokens
  live in `src/index.css`)
- Recharts for the fit-breakdown bar chart and language-breakdown donut
- No UI kit — small hand-built primitives in `src/components/ui`

## Design

Strictly monochrome: black canvas, off-white ink, and a scale of grays for
surfaces/borders — no color accents anywhere, including the verdict and
flag states, which are differentiated by weight, icon, and contrast rather
than color. Numbers (scores, stats, percentages) are set in JetBrains Mono
with tabular figures; everything else is Inter.

The signature visual is the **pipeline rail** (`src/components/pipeline/PipelineRail.tsx`),
a diagram of the actual LangGraph topology in `orchestrator/orchestrator.py`:

```
routing → [linkedin, github, web_research] (parallel) → fit_scorer → synthesizer
```

It's reused, unmodified, in three places: idle as a preview on the form,
animated live during a run (driven by SSE progress events), and as a static
trail if a job fails. On narrow screens it swaps to a vertical timeline.

## Running locally

```bash
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000` (see `vite.config.ts`),
so run the FastAPI backend on port 8000 alongside it — no `.env` needed for
local development. To point at a different backend, edit the `server.proxy`
block in `vite.config.ts`, or set up a reverse proxy in front of both apps in
production so the frontend can keep calling relative `/api/...` paths.

## API surface used

All typed in `src/types/api.ts`, all called from `src/lib/api.ts`:

- `POST /api/v1/research/start` — multipart form (LinkedIn/GitHub URLs, pasted
  text, resume/JD/culture file uploads) → `{ job_id, status }`
- `GET /api/v1/research/{job_id}/stream` — SSE; parsed manually via
  `ReadableStream` (not `EventSource`) so the connection can be cleanly aborted
  on unmount/reset
- `GET /api/v1/report/{job_id}` — the completed `FullReport`
- `POST /api/v1/report/{job_id}/export` — streams back a PDF blob for download

## Project structure

```
src/
  components/
    ui/          Button, Card, Badge, Input/Textarea — shared primitives
    form/         ResearchForm, FileDrop, SegmentedControl
    pipeline/      PipelineRail (signature diagram), ProgressView (log feed)
    report/        ReportHeader, ScoreRing, charts, flags, skills, etc.
  hooks/
    useResearchJob.ts   form → running → report/error state machine
  lib/
    api.ts          fetch wrappers + SSE parser
    format.ts        labels, date/number formatting
  types/
    api.ts          mirrors backend/models/schemas.py
```

## Notes

- Google Fonts (Inter, JetBrains Mono) are loaded via `<link>` tags in
  `index.html`; if you need to vendor fonts instead (e.g. for an offline or
  restricted environment), swap those links for local `@font-face` rules.
- The PDF export button calls the export endpoint directly and triggers a
  browser download; there's no separate viewer.
