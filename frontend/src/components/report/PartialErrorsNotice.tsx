export function PartialErrorsNotice({ errors }: { errors: Record<string, string> }) {
  const entries = Object.entries(errors);
  if (entries.length === 0) return null;

  return (
    <div className="rounded-2xl border border-dashed border-[var(--color-line-strong)] px-5 py-3.5">
      <p className="mb-1.5 text-[12px] font-medium uppercase tracking-[0.06em] text-[var(--color-ink-faint)]">
        Partial pipeline errors
      </p>
      <ul className="space-y-1">
        {entries.map(([agent, message]) => (
          <li key={agent} className="font-mono text-[12px] text-[var(--color-ink-faint)]">
            {agent}: {message}
          </li>
        ))}
      </ul>
    </div>
  );
}
