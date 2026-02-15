'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Tabs, type TabId } from './Tabs';
import { WorkspaceProvider, useWorkspace } from './WorkspaceContext';
import { CodePanel } from '@/components/code/CodePanel';
import { QAPanel } from '@/components/understanding/QAPanel';
import { ValidationPanel } from '@/components/validation/ValidationPanel';

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
  return (
    <WorkspaceProvider>
      <WorkspaceShellInner projectId={projectId} projectName={projectName} />
    </WorkspaceProvider>
  );
}

function WorkspaceShellInner({ projectId, projectName }: WorkspaceShellProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = parseTabFromSearchParams(searchParams);
  const fileParam = searchParams.get('file');
  const { selectedFilePath, setSelectedFilePath } = useWorkspace();

  const [codePanelOpen, setCodePanelOpen] = useState(() => {
    if (typeof window === 'undefined') return true;
    return !window.matchMedia('(max-width: 768px)').matches;
  });
  const [codePanelWidth, setCodePanelWidth] = useState(720);
  const [resizing, setResizing] = useState(false);
  const minCodeWidth = 200;
  const maxCodeWidth = 800;

  const setTab = useCallback(
    (newTab: TabId) => {
      const next = new URLSearchParams(searchParams.toString());
      next.set('tab', newTab);
      router.replace(`/project/${projectId}?${next.toString()}`, { scroll: false });
    },
    [projectId, router, searchParams]
  );

  useEffect(() => {
    if (fileParam) {
      try {
        setSelectedFilePath(decodeURIComponent(fileParam));
      } catch {
        setSelectedFilePath(null);
      }
    }
  }, [fileParam, setSelectedFilePath]);

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
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full">
      <header className="shrink-0 border-b border-[var(--border)] px-4 py-3">
        <h1 className="text-base font-semibold text-[var(--text)] truncate">
          {projectName || projectId}
        </h1>
        {projectName && (
          <p className="text-xs text-[var(--muted)] truncate">Project workspace</p>
        )}
      </header>

      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left: Persistent Code Panel (~60% width) */}
        <CodePanel
          projectId={projectId}
          selectedPath={selectedFilePath}
          onPathChange={setSelectedFilePath}
          width={codePanelWidth}
          isOpen={codePanelOpen}
          onToggleOpen={() => setCodePanelOpen(!codePanelOpen)}
          onResizerMouseDown={() => setResizing(true)}
          isResizing={resizing}
        />

        {/* Right: Chrome-style tabs + content */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden border-l border-[var(--border)] border-opacity-50 bg-[var(--card)]">
          <div className="shrink-0 pt-2 px-2 pb-0 bg-[var(--border)] bg-opacity-30 border-b border-[var(--border)]">
            <Tabs value={tab} onChange={setTab} tabs={TABS} />
          </div>
          {tab === 'understanding' ? (
            <div
              role="tabpanel"
              id="tabpanel-understanding"
              aria-labelledby="tab-understanding"
              tabIndex={0}
              className="flex-1 min-h-0 overflow-hidden flex flex-col"
            >
              <QAPanel
                projectId={projectId}
                onSelectedFilePathChange={setSelectedFilePath}
              />
            </div>
          ) : (
            <div
              role="tabpanel"
              id="tabpanel-validation"
              aria-labelledby="tab-validation"
              tabIndex={0}
              className="flex-1 min-h-0 overflow-y-auto px-6 py-6 w-full"
            >
              <ValidationPanel projectId={projectId} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
