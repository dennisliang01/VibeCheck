'use client';

import type { ValidationSection } from '@/lib/schemas';

interface ValidationSectionCardProps {
  section: ValidationSection;
  selected: boolean;
  onSelect: () => void;
}

function statusFromScore(score: number): string {
  if (score >= 80) return 'Good';
  if (score >= 50) return 'Okay';
  return 'Needs work';
}

export function ValidationSectionCard({ section, selected, onSelect }: ValidationSectionCardProps) {
  const status = statusFromScore(section.score);
  const hasDetails = section.details.length > 0;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)] ${
        selected
          ? 'border-[var(--accent)] bg-[var(--accent)]/10'
          : 'border-[var(--border)] bg-[var(--card)] hover:bg-[var(--bg)]/30'
      }`}
      aria-pressed={selected}
      aria-label={`${section.label}, score ${section.score}. ${hasDetails ? 'Click to view details.' : ''}`}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-[var(--text)] truncate">{section.label}</p>
          <p
            className={`mt-1 text-xs ${
              status === 'Good' ? 'text-[var(--success)]' : status === 'Okay' ? 'text-[var(--muted)]' : 'text-[var(--error)]'
            }`}
          >
            {status}
          </p>
        </div>
        <span className="text-xl font-semibold text-[var(--text)] shrink-0">{section.score}</span>
      </div>
    </button>
  );
}
