'use client';

interface FeedbackCardProps {
  id: string;
  title: string;
  severity: string;
  filePath?: string;
  recommendation: string;
  onJumpToFile?: (path: string) => void;
}

export function FeedbackCard({
  title,
  severity,
  filePath,
  recommendation,
  onJumpToFile,
}: FeedbackCardProps) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-[var(--text)]">{title}</h3>
          <p className="mt-1 text-xs text-[var(--muted)] capitalize">
            Severity: {severity}
          </p>
          {filePath && (
            <p className="mt-1 text-xs font-mono text-[var(--muted)] truncate">
              {filePath}
            </p>
          )}
          <p className="mt-2 text-sm text-[var(--text)]">{recommendation}</p>
        </div>
        {filePath && onJumpToFile && (
          <button
            type="button"
            onClick={() => onJumpToFile(filePath)}
            className="shrink-0 rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--accent)] hover:bg-[var(--accent)] hover:bg-opacity-10 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
          >
            Jump to file
          </button>
        )}
      </div>
    </div>
  );
}
