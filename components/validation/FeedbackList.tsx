'use client';

import { FeedbackCard } from './FeedbackCard';

interface FeedbackItem {
  id: string;
  title: string;
  severity: string;
  filePath?: string;
  recommendation: string;
}

interface FeedbackListProps {
  feedback: FeedbackItem[];
  onOpenCode?: (path: string) => void;
}

export function FeedbackList({ feedback, onOpenCode }: FeedbackListProps) {
  return (
    <div>
      <h2 className="text-sm font-medium text-[var(--text)] mb-3">
        Feedback
      </h2>
      <div className="space-y-3 max-h-[400px] overflow-y-auto">
        {feedback.map((item) => (
          <FeedbackCard
            key={item.id}
            id={item.id}
            title={item.title}
            severity={item.severity}
            filePath={item.filePath}
            recommendation={item.recommendation}
            onOpenCode={item.filePath ? onOpenCode : undefined}
          />
        ))}
      </div>
    </div>
  );
}
