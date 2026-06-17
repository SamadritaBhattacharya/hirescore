import * as React from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "outline";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-[var(--color-ink)] text-[var(--color-canvas)] hover:bg-white disabled:hover:bg-[var(--color-ink)]",
  secondary:
    "bg-[var(--color-surface-2)] text-[var(--color-ink)] hover:bg-[var(--color-surface-3)] border border-[var(--color-line)]",
  outline:
    "bg-transparent text-[var(--color-ink)] border border-[var(--color-line-strong)] hover:border-[var(--color-ink-dim)] hover:bg-[var(--color-surface)]",
  ghost:
    "bg-transparent text-[var(--color-ink-dim)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface)]",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5 rounded-lg",
  md: "h-10 px-4 text-sm gap-2 rounded-xl",
  lg: "h-12 px-6 text-[15px] gap-2 rounded-xl",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "primary", size = "md", loading, disabled, children, ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-colors duration-150",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          "focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)]",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {loading && (
          <svg
            className="size-3.5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              cx="12"
              cy="12"
              r="9"
              stroke="currentColor"
              strokeWidth="2.5"
              opacity="0.25"
            />
            <path
              d="M21 12a9 9 0 0 0-9-9"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
