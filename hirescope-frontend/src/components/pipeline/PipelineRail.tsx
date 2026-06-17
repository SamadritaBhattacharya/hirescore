import type { AgentName } from "@/types/api";
import { AGENT_LABELS } from "@/lib/format";
import { cn } from "@/lib/cn";

export type NodeStatus = "idle" | "active" | "done" | "failed";
export type StatusMap = Record<AgentName, NodeStatus>;

export const idleStatusMap: StatusMap = {
  routing: "idle",
  linkedin: "idle",
  github: "idle",
  web_research: "idle",
  fit_scorer: "idle",
  synthesizer: "idle",
};

const POS: Record<AgentName, { x: number; y: number }> = {
  routing: { x: 56, y: 100 },
  linkedin: { x: 300, y: 36 },
  github: { x: 300, y: 100 },
  web_research: { x: 300, y: 164 },
  fit_scorer: { x: 552, y: 100 },
  synthesizer: { x: 752, y: 100 },
};

const EDGES: { from: AgentName; to: AgentName }[] = [
  { from: "routing", to: "linkedin" },
  { from: "routing", to: "github" },
  { from: "routing", to: "web_research" },
  { from: "linkedin", to: "fit_scorer" },
  { from: "github", to: "fit_scorer" },
  { from: "web_research", to: "fit_scorer" },
  { from: "fit_scorer", to: "synthesizer" },
];

function edgePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2;
  return `M ${a.x + 22} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x - 22} ${b.y}`;
}

function rank(status: NodeStatus): number {
  return { idle: 0, active: 1, done: 2, failed: 2 }[status];
}

const ORDER: AgentName[] = [
  "routing",
  "linkedin",
  "github",
  "web_research",
  "fit_scorer",
  "synthesizer",
];

export function PipelineRail({
  statuses,
  className,
}: {
  statuses: StatusMap;
  className?: string;
}) {
  return (
    <>
      <svg
        viewBox="0 0 808 200"
        className={cn("hidden w-full sm:block", className)}
        role="img"
        aria-label="Agent research pipeline"
      >
        {/* edges */}
        {EDGES.map((e) => {
          const from = statuses[e.from];
          const to = statuses[e.to];
          const traveled = rank(from) >= 2 && rank(to) >= 1;
          const flowing = rank(from) >= 1 && to === "active";
          return (
            <path
              key={`${e.from}-${e.to}`}
              d={edgePath(POS[e.from], POS[e.to])}
              fill="none"
              strokeWidth={1.5}
              stroke={traveled ? "var(--color-ink-dim)" : "var(--color-line)"}
              strokeDasharray={flowing ? "4 4" : undefined}
              className={flowing ? "animate-dash" : undefined}
            />
          );
        })}

        {/* nodes */}
        {(Object.keys(POS) as AgentName[]).map((name) => {
          const status = statuses[name];
          const pos = POS[name];
          return (
            <g key={name} transform={`translate(${pos.x}, ${pos.y})`}>
              {status === "active" && (
                <circle r="22" fill="none" className="animate-pulse-ring" />
              )}
              <circle
                r="20"
                fill={
                  status === "done"
                    ? "var(--color-ink)"
                    : status === "failed"
                    ? "var(--color-surface)"
                    : "var(--color-surface-2)"
                }
                stroke={
                  status === "failed"
                    ? "var(--color-ink-dim)"
                    : status === "active"
                    ? "var(--color-ink)"
                    : status === "done"
                    ? "var(--color-ink)"
                    : "var(--color-line-strong)"
                }
                strokeWidth={1.5}
                strokeDasharray={status === "failed" ? "3 3" : undefined}
              />

              {status === "done" && (
                <path
                  d="M -7 0 L -2 6 L 8 -7"
                  stroke="var(--color-canvas)"
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              )}
              {status === "failed" && (
                <path
                  d="M -6 -6 L 6 6 M 6 -6 L -6 6"
                  stroke="var(--color-ink-dim)"
                  strokeWidth={2}
                  strokeLinecap="round"
                />
              )}
              {status === "active" && <circle r="5" fill="var(--color-ink)" />}

              <text
                y="38"
                textAnchor="middle"
                fontSize="11.5"
                fontFamily="var(--font-mono)"
                fill={status === "idle" ? "var(--color-ink-faint)" : "var(--color-ink-dim)"}
                letterSpacing="0.01em"
              >
                {AGENT_LABELS[name]}
              </text>
            </g>
          );
        })}
      </svg>

      <MobilePipelineList statuses={statuses} className={cn("sm:hidden", className)} />
    </>
  );
}

const STATUS_TEXT: Record<NodeStatus, string> = {
  idle: "Pending",
  active: "Running",
  done: "Done",
  failed: "Failed",
};

function MobilePipelineList({
  statuses,
  className,
}: {
  statuses: StatusMap;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col", className)}>
      {ORDER.map((name, i) => {
        const status = statuses[name];
        const last = i === ORDER.length - 1;
        return (
          <div key={name} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "relative flex size-3 shrink-0 items-center justify-center rounded-full border",
                  status === "done" && "border-[var(--color-ink)] bg-[var(--color-ink)]",
                  status === "active" && "border-[var(--color-ink)] bg-[var(--color-surface-2)] animate-pulse-ring",
                  status === "idle" && "border-[var(--color-line-strong)] bg-[var(--color-surface-2)]",
                  status === "failed" && "border-dashed border-[var(--color-ink-dim)] bg-[var(--color-surface)]"
                )}
              />
              {!last && <span className="my-0.5 h-5 w-px bg-[var(--color-line)]" />}
            </div>
            <div className="pb-5 -mt-0.5">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "text-[13px] font-medium",
                    status === "idle" ? "text-[var(--color-ink-faint)]" : "text-[var(--color-ink)]"
                  )}
                >
                  {AGENT_LABELS[name]}
                </span>
                <span className="font-mono text-[10.5px] text-[var(--color-ink-faint)]">
                  {STATUS_TEXT[status]}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
