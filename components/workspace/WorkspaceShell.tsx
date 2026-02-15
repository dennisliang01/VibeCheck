'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Tabs, type TabId } from './Tabs';
import { CodePanel } from '@/components/understanding/CodePanel';
import { QAPanel } from '@/components/understanding/QAPanel';
import { ScoreGrid } from '@/components/validation/ScoreGrid';
import { FeedbackList } from '@/components/validation/FeedbackList';

interface WorkspaceShellProps {
  projectId: string;
  projectName?: string;
}

const TABS: { id: TabId; label: string }[] = [
  { id: 'understanding', label: 'Understanding' },
  { id: 'validation', label: 'Validation' },
];

function parseTabFromSearchParams(params: URLSearchParams): TabId {
  const t = params.get('tab');
  if (t === 'understanding' || t === 'validation') return t;
  return 'understanding';
}

export function WorkspaceShell({ projectId, projectName }: WorkspaceShellProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = parseTabFromSearchParams(searchParams);
  const fileParam = searchParams.get('file');

  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [validationData, setValidationData] = useState<{
    scores: { performance: number; security: number; codeQuality: number; architecture: number };
    feedback: Array<{ id: string; title: string; severity: string; filePath?: string; recommendation: string }>;
  } | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);

  const setTab = useCallback(
    (newTab: TabId) => {
      const next = new URLSearchParams(searchParams.toString());
      next.set('tab', newTab);
      router.replace(`/project/${projectId}?${next.toString()}`, { scroll: false });
    },
    [projectId, router, searchParams]
  );

  // Sync file param to selected path (e.g. from Jump to file)
  useEffect(() => {
    if (fileParam) {
      try {
        const decoded = decodeURIComponent(fileParam);
        setSelectedFilePath(decoded);
      } catch {
        setSelectedFilePath(null);
      }
    }
  }, [fileParam]);

  const onJumpToFile = useCallback(
    (path: string) => {
      setSelectedFilePath(path);
      setTab('understanding');
      const next = new URLSearchParams(searchParams.toString());
      next.set('tab', 'understanding');
      next.set('file', encodeURIComponent(path));
      router.replace(`/project/${projectId}?${next.toString()}`, { scroll: false });
    },
    [projectId, router, searchParams, setTab]
  );

  // Fetch validation data when Validation tab is shown
  useEffect(() => {
    if (tab !== 'validation') return;
    setValidationLoading(true);
    fetch(`/api/project/${projectId}/validation`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setValidationData(data);
      })
      .finally(() => setValidationLoading(false));
  }, [tab, projectId]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full">
      {/* Header */}
      <header className="shrink-0 grid grid-cols-[1fr_auto_1fr] items-center gap-4 border-b border-[var(--border)] px-4 py-3">
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-[var(--text)] truncate">
            {projectName || projectId}
          </h1>
          {projectName && (
            <p className="text-xs text-[var(--muted)] truncate">Project workspace</p>
          )}
        </div>
        <div className="flex justify-center">
          <Tabs value={tab} onChange={setTab} tabs={TABS} />
        </div>
        <div className="flex justify-end">
          <Link
            href="/"
            className="text-xs text-[var(--muted)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded shrink-0"
          >
            ← Home
          </Link>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {tab === 'understanding' ? (
          <UnderstandingTab
            projectId={projectId}
            selectedFilePath={selectedFilePath}
            onSelectedFilePathChange={setSelectedFilePath}
          />
        ) : (
          <div
            role="tabpanel"
            id="tabpanel-validation"
            aria-labelledby="tab-validation"
            tabIndex={0}
            className="h-full overflow-y-auto px-6 py-6"
          >
            {validationLoading ? (
              <p className="text-[var(--muted)]">Loading validation…</p>
            ) : validationData ? (
              <div className="space-y-6 max-w-4xl">
                <ScoreGrid scores={validationData.scores} />
                <FeedbackList
                  feedback={validationData.feedback}
                  onJumpToFile={onJumpToFile}
                />
              </div>
            ) : (
              <p className="text-[var(--muted)]">Could not load validation data.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function UnderstandingTab({
  projectId,
  selectedFilePath,
  onSelectedFilePathChange,
}: {
  projectId: string;
  selectedFilePath: string | null;
  onSelectedFilePathChange: (path: string | null) => void;
}) {
  const [codePanelOpen, setCodePanelOpen] = useState(true);
  const [codePanelWidth, setCodePanelWidth] = useState(400);
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
    <div
      role="tabpanel"
      id="tabpanel-understanding"
      aria-labelledby="tab-understanding"
      tabIndex={0}
      className="h-full flex overflow-hidden"
    >
      <CodePanel
        projectId={projectId}
        selectedPath={selectedFilePath}
        onPathChange={onSelectedFilePathChange}
        width={codePanelWidth}
        isOpen={codePanelOpen}
        onToggleOpen={() => setCodePanelOpen(!codePanelOpen)}
        onResizerMouseDown={() => setResizing(true)}
        isResizing={resizing}
      />
      <QAPanel
        projectId={projectId}
        onSelectedFilePathChange={onSelectedFilePathChange}
      />
    </div>
  );
}
