import { cn } from "@/lib/cn";

interface SegmentedControlProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: { label: string; value: T }[];
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: SegmentedControlProps<T>) {
  return (
    <div className="inline-flex rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-[7px] px-3 py-1 text-[12.5px] font-medium transition-colors",
            value === opt.value
              ? "bg-[var(--color-ink)] text-[var(--color-canvas)]"
              : "text-[var(--color-ink-faint)] hover:text-[var(--color-ink-dim)]"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
