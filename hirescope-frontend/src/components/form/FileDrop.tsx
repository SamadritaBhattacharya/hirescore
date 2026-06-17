import * as React from "react";
import { cn } from "@/lib/cn";

interface FileDropProps {
  label: string;
  hint?: string;
  file: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
}

export function FileDrop({ label, hint, file, onChange, accept }: FileDropProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = React.useState(false);

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) onChange(files[0]);
  };

  return (
    <div>
      <span className="mb-1.5 block text-[13px] font-medium text-[var(--color-ink)]">
        {label}
      </span>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex h-10 cursor-pointer items-center justify-between gap-2 rounded-xl border border-dashed px-3.5 text-sm transition-colors",
          dragging
            ? "border-[var(--color-ink-dim)] bg-[var(--color-surface-2)]"
            : "border-[var(--color-line)] bg-[var(--color-surface-2)] hover:border-[var(--color-line-strong)]"
        )}
      >
        <span
          className={cn(
            "truncate",
            file ? "text-[var(--color-ink)]" : "text-[var(--color-ink-faint)]"
          )}
        >
          {file ? file.name : "Drop a file or click to browse"}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          {file && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="text-[var(--color-ink-faint)] hover:text-[var(--color-ink)]"
              aria-label="Remove file"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            className="text-[var(--color-ink-faint)]"
          >
            <path
              d="M12 16V4m0 0L7 9m5-5l5 5M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
      {hint && (
        <span className="mt-1.5 block text-[12px] text-[var(--color-ink-faint)]">
          {hint}
        </span>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
