import { Button } from "@/components/ui/Button";

export function TopBar({
  showReset,
  onReset,
}: {
  showReset: boolean;
  onReset: () => void;
}) {
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--color-line)] bg-[var(--color-canvas)]/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
        <button onClick={onReset} className="flex items-center gap-2.5">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9.5" stroke="var(--color-ink)" strokeWidth="1.6" />
            <path
              d="M12 6.5v5.2l3.6 2.1"
              stroke="var(--color-ink)"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-[14.5px] font-semibold tracking-tight text-[var(--color-ink)]">
            HireScope
          </span>
          <span className="hidden font-mono text-[11px] text-[var(--color-ink-faint)] sm:inline">
            candidate research agent
          </span>
        </button>
        {showReset && (
          <Button variant="ghost" size="sm" onClick={onReset}>
            New research
          </Button>
        )}
      </div>
    </header>
  );
}
