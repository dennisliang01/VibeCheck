'use client';

import { ScoreCard } from './ScoreCard';

interface ValidationScores {
  performance: number;
  security: number;
  codeQuality: number;
  architecture: number;
}

interface ScoreGridProps {
  scores: ValidationScores;
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
