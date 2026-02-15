'use client';

function statusFromScore(score: number): string {
  if (score >= 80) return 'Good';
  if (score >= 50) return 'Okay';
  return 'Needs work';
}

interface ScoreCardProps {
  label: string;
  score: number;
}

export function ScoreCard({ label, score }: ScoreCardProps) {
  const status = statusFromScore(score);
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
      <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-[var(--text)]">{score}</p>
      <p
        className={`mt-1 text-xs ${
          status === 'Good'
            ? 'text-[var(--success)]'
            : status === 'Okay'
              ? 'text-[var(--muted)]'
              : 'text-[var(--error)]'
        }`}
      >
        {status}
      </p>
    </div>
  );
}
