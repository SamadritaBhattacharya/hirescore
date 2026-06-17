import { clamp } from "@/lib/format";

interface Props {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

export function ScoreRing({ value, size = 132, strokeWidth = 7, label, sublabel }: Props) {
  const v = clamp(value, 0, 100);
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-ink)"
          strokeWidth={strokeWidth}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-[28px] font-semibold leading-none text-[var(--color-ink)] font-tnum">
          {Math.round(v)}
        </span>
        {label && (
          <span className="mt-1 text-[10.5px] uppercase tracking-[0.08em] text-[var(--color-ink-faint)]">
            {label}
          </span>
        )}
      </div>
      {sublabel && (
        <span className="absolute -bottom-5 text-[11px] text-[var(--color-ink-faint)] whitespace-nowrap">
          {sublabel}
        </span>
      )}
    </div>
  );
}
