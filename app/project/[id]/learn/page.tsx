'use client';

import { useParams } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useToast } from '@/components/ToastContext';

const FileSelectionContext = createContext<{
  selectedPath: string | null;
  setSelectedPath: (path: string) => void;
}>({ selectedPath: null, setSelectedPath: () => {} });

interface QuestionObj {
  id: string;
  topicId: string;
  category?: string;
  question: string;
  hint?: string;
  expectedConcepts?: string[];
}

interface GradeObj {
  score: number;
  feedback: string;
  correctPoints?: string[];
  missedPoints?: string[];
  nextRecommendedTopicId?: string;
}

interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
  isFile: boolean;
}

function HintReveal({ hint }: { hint: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="text-sm text-[var(--accent)] hover:underline"
      >
        {show ? 'Hide hint' : 'Show hint'}
      </button>
      {show && (
        <p className="mt-1.5 text-sm text-[var(--muted)]">{hint}</p>
      )}
    </div>
  );
}

export default function LearnPage() {
  const params = useParams();
  const { showToast } = useToast();
  const id = params.id as string;
  const [question, setQuestion] = useState<QuestionObj | null>(null);
  const [answer, setAnswer] = useState('');
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [grading, setGrading] = useState(false);
  const [lastGrade, setLastGrade] = useState<GradeObj | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchQuestion = useCallback(async () => {
    setError(null);
    setLoadingQuestion(true);
    setLastGrade(null);
    try {
      const res = await fetch(`/api/project/${id}/question`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load question');
      setQuestion(data);
      setAnswer('');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load question';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoadingQuestion(false);
    }
  }, [id, showToast]);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  const submitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question) return;
    setError(null);
    setGrading(true);
    try {
      const res = await fetch(`/api/project/${id}/grade`, {
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
    } finally {
      setGrading(false);
    }
  };

  const [codePanelOpen, setCodePanelOpen] = useState(true);
  const [codePanelWidth, setCodePanelWidth] = useState(320);
  const [treeOpen, setTreeOpen] = useState(true);
  const [resizing, setResizing] = useState(false);

  const minCodeWidth = 200;
  const maxCodeWidth = 800;

  useEffect(() => {
    if (!resizing) return;
    const onMove = (e: MouseEvent) => {
      const w = e.clientX;
      if (w >= minCodeWidth && w <= maxCodeWidth) setCodePanelWidth(w);
    };
    const onUp = () => setResizing(false);
    const prevCursor = document.body.style.cursor;
    const prevSelect = document.body.style.userSelect;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = prevCursor;
      document.body.style.userSelect = prevSelect;
    };
  }, [resizing]);

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden">
      {/* Left: Minimal code viewer (resizable, collapsible) */}
      {codePanelOpen ? (
        <>
          <section
            className="flex shrink-0 flex-col border-r border-[var(--border)] border-opacity-60 bg-[var(--bg)]"
            style={{ width: codePanelWidth, minWidth: minCodeWidth, maxWidth: maxCodeWidth }}
          >
            <div className="flex items-center justify-between border-b border-[var(--border)] border-opacity-60 px-2 py-1">
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  onClick={() => setTreeOpen((o) => !o)}
                  className="rounded p-1 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)]"
                  title={treeOpen ? 'Hide file tree' : 'Show file tree'}
                  aria-label={treeOpen ? 'Hide file tree' : 'Show file tree'}
                >
                  {treeOpen ? '⊟' : '⊞'}
                </button>
                <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] opacity-80">
                  Code
                </span>
              </div>
              <button
                type="button"
                onClick={() => setCodePanelOpen(false)}
                className="rounded p-1 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)]"
                title="Collapse code viewer"
                aria-label="Collapse code viewer"
              >
                ←
              </button>
            </div>
            <div className="flex flex-1 min-h-0">
              <FileSelectionProvider>
                {treeOpen ? (
                  <>
                    <FileTree projectId={id} />
                    <FileViewer projectId={id} />
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => setTreeOpen(true)}
                      className="shrink-0 w-6 border-r border-[var(--border)] border-opacity-40 bg-[var(--bg)] text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)]"
                      title="Show file tree"
                      aria-label="Show file tree"
                    >
                      ▶
                    </button>
                    <FileViewer projectId={id} />
                  </>
                )}
              </FileSelectionProvider>
            </div>
          </section>
          <div
            role="separator"
            aria-orientation="vertical"
            onMouseDown={() => setResizing(true)}
            className={`shrink-0 w-2 cursor-col-resize border-r border-[var(--border)] border-opacity-60 bg-transparent hover:bg-[var(--accent)] hover:bg-opacity-20 ${resizing ? 'bg-[var(--accent)] bg-opacity-30' : ''}`}
            title="Drag to resize code panel"
          />
        </>
      ) : (
        <button
          type="button"
          onClick={() => setCodePanelOpen(true)}
          className="shrink-0 w-8 border-r border-[var(--border)] border-opacity-60 bg-[var(--bg)] py-4 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)]"
          title="Show code viewer"
          aria-label="Show code viewer"
        >
          →
        </button>
      )}

      {/* Right: Question panel (emphasis) */}
      <section className="flex flex-1 flex-col min-w-0 bg-[var(--card)] border-l border-[var(--border)] border-opacity-30">
        <div className="border-b border-[var(--border)] border-opacity-50 px-6 py-3">
          <span className="text-xs font-medium uppercase tracking-wider text-[var(--accent)]">
            Question
          </span>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6 md:px-8 md:py-8">
          {error && (
            <p className="mb-4 text-sm text-[var(--error)]">{error}</p>
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
              {question.hint && (
                <HintReveal hint={question.hint} />
              )}

              {!lastGrade ? (
                <form onSubmit={submitAnswer} className="mt-6 max-w-xl space-y-4">
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Your answer…"
                    rows={6}
                    className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--bg)] px-4 py-3 font-mono text-sm focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  />
                  <div className="flex justify-start">
                    <button
                      type="submit"
                      disabled={grading}
                      className="rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
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
                    {lastGrade.correctPoints &&
                      lastGrade.correctPoints.length > 0 && (
                        <ul className="mt-2 list-inside list-disc text-sm text-[var(--success)]">
                          {lastGrade.correctPoints.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      )}
                    {lastGrade.missedPoints &&
                      lastGrade.missedPoints.length > 0 && (
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
                      className="rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
                    >
                      Next question →
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-[var(--muted)]">
              Could not load a question.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

function FileSelectionProvider({ children }: { children: React.ReactNode }) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const value = { selectedPath, setSelectedPath };
  return (
    <FileSelectionContext.Provider value={value}>
      {children}
    </FileSelectionContext.Provider>
  );
}

function FileTree({ projectId }: { projectId: string }) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set(['']));

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/project/${projectId}/tree`)
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (!cancelled && data) setTree(data);
      });
    return () => { cancelled = true; };
  }, [projectId]);

  const toggle = (path: string) => {
    setOpenDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  if (!tree) {
    return (
      <div className="w-36 shrink-0 border-r border-[var(--border)] border-opacity-40 p-2">
        <p className="text-[10px] text-[var(--muted)]">Loading…</p>
      </div>
    );
  }

  return (
    <FileSelectionContext.Consumer>
      {({ selectedPath }) => (
        <div className="w-36 shrink-0 overflow-y-auto border-r border-[var(--border)] border-opacity-40 py-0.5 font-mono text-[11px]">
          <TreeNodes
            node={tree}
            projectId={projectId}
            openDirs={openDirs}
            onToggle={toggle}
            depth={0}
            selectedPath={selectedPath}
          />
        </div>
      )}
    </FileSelectionContext.Consumer>
  );
}

function TreeNodes({
  node,
  projectId,
  openDirs,
  onToggle,
  depth,
  selectedPath,
}: {
  node: TreeNode;
  projectId: string;
  openDirs: Set<string>;
  onToggle: (path: string) => void;
  depth: number;
  selectedPath: string | null;
}) {
  const isOpen = openDirs.has(node.path);
  const hasChildren = node.children && node.children.length > 0;

  if (node.isFile) {
    return (
      <FileItem
        path={node.path}
        name={node.name}
        depth={depth}
        selected={selectedPath === node.path}
      />
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => hasChildren && onToggle(node.path)}
        className="flex w-full items-center gap-0.5 py-0.5 pr-1 text-left hover:bg-[var(--card)]"
        style={{ paddingLeft: `${depth * 8 + 6}px` }}
      >
        <span className="w-3 shrink-0 text-[10px] text-[var(--muted)]">
          {hasChildren ? (isOpen ? '▼' : '▶') : ''}
        </span>
        <span className="truncate text-[var(--muted)]">{node.name}</span>
      </button>
      {hasChildren && isOpen && (
        <div>
          {node.children!.map((c) => (
            <TreeNodes
              key={c.path}
              node={c}
              projectId={projectId}
              openDirs={openDirs}
              onToggle={onToggle}
              depth={depth + 1}
              selectedPath={selectedPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FileItem({
  path,
  name,
  depth,
  selected,
}: {
  path: string;
  name: string;
  depth: number;
  selected: boolean;
}) {
  const { setSelectedPath } = useContext(FileSelectionContext);
  return (
    <button
      type="button"
      onClick={() => setSelectedPath(path)}
      className={`flex w-full items-center gap-0.5 py-0.5 pr-1 text-left hover:bg-[var(--card)] ${selected ? 'bg-[var(--card)] text-[var(--accent)]' : ''}`}
      style={{ paddingLeft: `${depth * 8 + 6}px` }}
    >
      <span className="w-3 shrink-0" />
      <span className="truncate text-[11px]">{name}</span>
    </button>
  );
}

function FileViewer({ projectId }: { projectId: string }) {
  const { selectedPath } = useContext(FileSelectionContext);
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedPath) {
      setContent(null);
      return;
    }
    setLoading(true);
    fetch(`/api/project/${projectId}/file?path=${encodeURIComponent(selectedPath)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setContent(data?.content ?? null);
      })
      .finally(() => setLoading(false));
  }, [projectId, selectedPath]);

  if (!selectedPath) {
    return (
      <div className="flex flex-1 items-center justify-center text-[11px] text-[var(--muted)] opacity-80">
        Select a file
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-[11px] text-[var(--muted)]">
        …
      </div>
    );
  }

  const lines = (content ?? '').split(/\r?\n/);
  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
      <div className="border-b border-[var(--border)] border-opacity-40 px-2 py-1 text-[10px] text-[var(--muted)] truncate">
        {selectedPath}
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="min-h-full font-mono text-[11px] leading-snug text-[var(--text)] p-2">
          <code>
            {lines.map((line, i) => (
              <div key={i} className="table-row">
                <span className="table-cell w-6 select-none pr-2 text-right text-[var(--muted)] opacity-70">
                  {i + 1}
                </span>
                <span className="table-cell whitespace-pre break-all">
                  {line || ' '}
                </span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
