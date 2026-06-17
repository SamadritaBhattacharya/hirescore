import * as React from "react";
import { cn } from "@/lib/cn";

type Tone = "default" | "strong" | "muted" | "outline";

export function Badge({
  className,
  tone = "default",
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  const toneClasses: Record<Tone, string> = {
    default: "bg-[var(--color-surface-2)] text-[var(--color-ink)] border border-[var(--color-line)]",
    strong: "bg-[var(--color-ink)] text-[var(--color-canvas)] border border-[var(--color-ink)]",
    muted: "bg-transparent text-[var(--color-ink-faint)] border border-[var(--color-line-soft)]",
    outline: "bg-transparent text-[var(--color-ink-dim)] border border-[var(--color-line-strong)]",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[12px] font-medium leading-none",
        toneClasses[tone],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
