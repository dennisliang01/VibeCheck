'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@/components/ToastContext';

interface QuestionObj {
  id: string;
  topicId: string;
  category?: string;
  question: string;
  hint?: string;
  fileHints?: string[];
}

interface GradeObj {
  score: number;
  feedback: string;
  correctPoints?: string[];
  missedPoints?: string[];
  nextRecommendedTopicId?: string;
}

interface QAPanelProps {
  projectId: string;
  onSelectedFilePathChange: (path: string | null) => void;
}

function HintReveal({ hint }: { hint: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="text-sm text-[var(--accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)] rounded"
      >
        {show ? 'Hide hint' : 'Show hint'}
      </button>
      {show && (
        <p className="mt-1.5 text-sm text-[var(--muted)]">{hint}</p>
      )}
    </div>
  );
}

export function QAPanel({
  projectId,
  onSelectedFilePathChange,
}: QAPanelProps) {
  const { showToast } = useToast();
  const [question, setQuestion] = useState<QuestionObj | null>(null);
  const [answer, setAnswer] = useState('');
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [grading, setGrading] = useState(false);
  const [lastGrade, setLastGrade] = useState<GradeObj | null>(null);
  const [error, setError] = useState<string | null>(null);
  const answerErrorRef = useRef<HTMLParagraphElement>(null);
  const answerInputRef = useRef<HTMLTextAreaElement>(null);

  const fetchQuestion = useCallback(async () => {
    setError(null);
    setLoadingQuestion(true);
    setLastGrade(null);
    try {
      const res = await fetch(`/api/project/${projectId}/question`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load question');
      setQuestion(data);
      setAnswer('');
      if (data.fileHints?.[0]) {
        onSelectedFilePathChange(data.fileHints[0]);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load question';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoadingQuestion(false);
    }
  }, [projectId, showToast, onSelectedFilePathChange]);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  const submitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question) return;
    setError(null);
    setGrading(true);
    try {
      const res = await fetch(`/api/project/${projectId}/grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          questionObj: question,
          userAnswer: answer,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Grade failed');
      setLastGrade(data.grade);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Grade failed';
      setError(msg);
      showToast(msg, 'error');
      requestAnimationFrame(() => answerErrorRef.current?.focus() ?? answerInputRef.current?.focus());
    } finally {
      setGrading(false);
    }
  };

  return (
    <section
        className="flex flex-1 flex-col min-w-0 bg-[var(--card)] border-l border-[var(--border)] border-opacity-30"
        aria-labelledby="learn-heading"
      >
        <div className="border-b border-[var(--border)] border-opacity-50 px-6 py-3">
          <h2 id="learn-heading" className="text-xs font-medium uppercase tracking-wider text-[var(--accent)]">
            Question
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6 md:px-8 md:py-8">
          {error && (
            <p id="answer-error" ref={answerErrorRef} className="mb-4 text-sm text-[var(--error)]" tabIndex={-1} role="alert">
              {error}
            </p>
          )}
          {loadingQuestion ? (
            <p className="text-[var(--muted)]">Loading question…</p>
          ) : question ? (
            <>
              {question.category && (
                <p className="mb-3">
                  <span className="inline-flex items-center rounded-md bg-[var(--card)] border border-[var(--border)] px-2.5 py-1 text-xs font-medium text-[var(--muted)]">
                    {question.category}
                  </span>
                </p>
              )}
              <p className="whitespace-pre-wrap text-base leading-relaxed text-[var(--text)] md:text-lg">
                {question.question}
              </p>
              {question.hint && <HintReveal hint={question.hint} />}

              {!lastGrade ? (
                <form onSubmit={submitAnswer} className="mt-6 max-w-xl space-y-4">
                  <label htmlFor="answer-input" className="sr-only">
                    Your answer
                  </label>
                  <textarea
                    ref={answerInputRef}
                    id="answer-input"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Your answer…"
                    rows={6}
                    aria-describedby={error ? 'answer-error' : undefined}
                    className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--bg)] px-4 py-3 font-mono text-sm focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  />
                  <div className="flex justify-start">
                    <button
                      type="submit"
                      disabled={grading}
                      className="rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
                    >
                      {grading ? 'Grading…' : 'Submit'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="mt-6 max-w-xl space-y-4">
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-4">
                    <p className="mb-2">
                      <span className="font-medium">Score: </span>
                      <span
                        className={
                          lastGrade.score >= 70
                            ? 'text-[var(--success)]'
                            : 'text-[var(--error)]'
                        }
                      >
                        {lastGrade.score}%
                      </span>
                    </p>
                    <p className="text-[var(--muted)]">{lastGrade.feedback}</p>
                    {lastGrade.correctPoints && lastGrade.correctPoints.length > 0 && (
                      <ul className="mt-2 list-inside list-disc text-sm text-[var(--success)]">
                        {lastGrade.correctPoints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    )}
                    {lastGrade.missedPoints && lastGrade.missedPoints.length > 0 && (
                      <ul className="mt-1 list-inside list-disc text-sm text-[var(--error)]">
                        {lastGrade.missedPoints.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="flex justify-start">
                    <button
                      type="button"
                      onClick={fetchQuestion}
                      className="rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
                    >
                      Next question →
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-[var(--muted)]">Could not load a question.</p>
          )}
        </div>
      </section>
  );
}
