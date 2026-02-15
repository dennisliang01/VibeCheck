'use client';

import { useEffect, useState } from 'react';
import { ScoreGrid } from './ScoreGrid';
import { FeedbackList } from './FeedbackList';
import { useWorkspace } from '@/components/workspace/WorkspaceContext';

interface ValidationPanelProps {
  projectId: string;
}

export function ValidationPanel({ projectId }: ValidationPanelProps) {
  const { onOpenCode } = useWorkspace();
  const [data, setData] = useState<{
    scores: { performance: number; security: number; codeQuality: number; architecture: number };
    feedback: Array<{ id: string; title: string; severity: string; filePath?: string; recommendation: string }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/project/${projectId}/validation`)
      .then((res) => (res.ok ? res.json() : null))
      .then((d) => d && setData(d))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return <p className="text-[var(--muted)]">Loading validation…</p>;
  }
  if (!data) {
    return <p className="text-[var(--muted)]">Could not load validation data.</p>;
  }

  return (
    <div className="space-y-6 w-full max-w-full">
      <ScoreGrid scores={data.scores} />
      <FeedbackList
        feedback={data.feedback}
        onOpenCode={onOpenCode}
      />
    </div>
  );
}
