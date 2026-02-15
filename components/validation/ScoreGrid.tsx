'use client';

interface ValidationScores {
  performance: number;
  security: number;
  codeQuality: number;
  architecture: number;
}

interface ScoreGridProps {
  scores: ValidationScores;
}

function statusFromScore(score: number): string {
  if (score >= 80) return 'Good';
  if (score >= 50) return 'Okay';
  return 'Needs work';
}

function ScoreCard({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
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

export function ScoreGrid({ scores }: ScoreGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <ScoreCard label="Performance" score={scores.performance} />
      <ScoreCard label="Security" score={scores.security} />
      <ScoreCard label="Code Quality" score={scores.codeQuality} />
      <ScoreCard label="Architecture" score={scores.architecture} />
    </div>
  );
}
