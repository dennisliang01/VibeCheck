'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@/components/ToastContext';

const CATEGORY_PALETTE = [
  'var(--category-ui)',
  'var(--category-functionality)',
  'var(--category-performance)',
  'var(--category-data)',
  'var(--category-security)',
  'var(--category-general)',
];

interface QuestionObj {
  id: string;
  topicId: string;
  category?: string;
  categories?: string[];
  question: string;
  hint?: string;
  fileHints?: string[];
}

function categoryColor(index: number): string {
  return CATEGORY_PALETTE[index % CATEGORY_PALETTE.length];
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
  selectedFilePath: string | null;
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
  selectedFilePath,
}: QAPanelProps) {
  const { showToast } = useToast();
  const [categories, setCategories] = useState<string[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | 'Any'>('Any');
  const [question, setQuestion] = useState<QuestionObj | null>(null);
  const [answer, setAnswer] = useState('');
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [grading, setGrading] = useState(false);
  const [lastGrade, setLastGrade] = useState<GradeObj | null>(null);
  const [error, setError] = useState<string | null>(null);
  const answerErrorRef = useRef<HTMLParagraphElement>(null);
  const answerInputRef = useRef<HTMLTextAreaElement>(null);
  const selectedFilePathRef = useRef(selectedFilePath);
  selectedFilePathRef.current = selectedFilePath;

  const fetchQuestion = useCallback(async () => {
    setError(null);
    setLoadingQuestion(true);
    setLastGrade(null);
    const categoryParam =
      selectedCategory && selectedCategory !== 'Any' ? `?category=${encodeURIComponent(selectedCategory)}` : '';
    try {
      const res = await fetch(`/api/project/${projectId}/question${categoryParam}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load question');
      setQuestion(data);
      setAnswer('');
      if (data.fileHints?.[0] && !selectedFilePathRef.current) {
        onSelectedFilePathChange(data.fileHints[0]);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load question';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoadingQuestion(false);
    }
  }, [projectId, selectedCategory, showToast, onSelectedFilePathChange]);

  useEffect(() => {
    fetch(`/api/project/${projectId}/question/categories`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data?.categories && setCategories(data.categories))
      .finally(() => setCategoriesLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  const handleCategorySelect = (cat: string | 'Any') => {
    setSelectedCategory(cat);
    setQuestion(null);
    setLastGrade(null);
  };

  const doSubmit = async () => {
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

  const submitAnswer = (e: React.FormEvent) => {
    e.preventDefault();
    doSubmit();
  };

  return (
    <section
        className="flex flex-1 flex-col min-w-0 min-h-0 bg-[var(--card)] border-l border-[var(--border)] border-opacity-30"
        aria-label="Understanding questions"
      >
        <div className="shrink-0 border-b border-[var(--border)] border-opacity-50 px-6 py-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleCategorySelect('Any')}
              className={`rounded-md px-3 py-1.5 text-xs font-medium border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)] ${
                selectedCategory === 'Any'
                  ? 'border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--accent)]'
                  : 'border-[var(--border)] bg-[var(--bg)] text-[var(--muted)] hover:bg-[var(--border)]/50'
              }`}
            >
              Any
            </button>
            {!categoriesLoading &&
              categories.map((cat, i) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleCategorySelect(cat)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)] ${
                    selectedCategory === cat
                      ? 'text-white'
                      : 'opacity-70 hover:opacity-100'
                  }`}
                  style={{
                    backgroundColor: selectedCategory === cat ? categoryColor(i) : 'var(--card)',
                    borderColor: selectedCategory === cat ? categoryColor(i) : 'var(--border)',
                  }}
                >
                  {cat}
                </button>
              ))}
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-6 md:px-8 md:py-8">
          {error && (
            <p id="answer-error" ref={answerErrorRef} className="mb-4 text-sm text-[var(--error)]" tabIndex={-1} role="alert">
              {error}
            </p>
          )}
          {loadingQuestion ? (
            <p className="text-[var(--muted)]">Loading question…</p>
          ) : question ? (
            <>
              <p className="whitespace-pre-wrap text-base leading-relaxed text-[var(--text)] md:text-lg">
                {question.question}
              </p>
              {question.hint && <HintReveal hint={question.hint} />}

              {!lastGrade ? (
                <form onSubmit={submitAnswer} className="mt-6 w-full max-w-xl lg:max-w-none space-y-4">
                  <label htmlFor="answer-input" className="sr-only">
                    Your answer (press Enter to submit)
                  </label>
                  <textarea
                    ref={answerInputRef}
                    id="answer-input"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (question && !grading) doSubmit();
                      }
                    }}
                    placeholder="Your answer… (Enter to submit)"
                    rows={6}
                    aria-describedby={error ? 'answer-error' : undefined}
                    className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--bg)] px-4 py-3 font-mono text-sm focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  />
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={grading}
                      className="rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
                      title="Submit answer (Enter)"
                    >
                      {grading ? 'Grading…' : 'Submit (↵)'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="mt-6 w-full max-w-xl lg:max-w-none space-y-4">
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
                  <div className="flex justify-end">
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
