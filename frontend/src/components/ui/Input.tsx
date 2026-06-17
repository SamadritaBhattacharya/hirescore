import * as React from "react";
import { cn } from "@/lib/cn";

export function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline gap-1.5 text-[13px] font-medium text-[var(--color-ink)]">
        {label}
        {required && <span className="text-[var(--color-ink-faint)]">required</span>}
      </span>
      {children}
      {hint && (
        <span className="mt-1.5 block text-[12px] text-[var(--color-ink-faint)]">
          {hint}
        </span>
      )}
    </label>
  );
}

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-10 w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3.5 text-sm text-[var(--color-ink)]",
      "placeholder:text-[var(--color-ink-faint)]",
      "transition-colors focus:border-[var(--color-line-strong)] focus:outline-none focus:ring-1 focus:ring-[var(--color-ink-faint)]",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full resize-none rounded-xl border border-[var(--color-line)] bg-[var(--color-surface-2)] px-3.5 py-2.5 text-sm text-[var(--color-ink)]",
      "placeholder:text-[var(--color-ink-faint)]",
      "transition-colors focus:border-[var(--color-line-strong)] focus:outline-none focus:ring-1 focus:ring-[var(--color-ink-faint)]",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
