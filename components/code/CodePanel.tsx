'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useTheme } from '@/components/ThemeContext';

const FileSelectionContext = createContext<{
  selectedPath: string | null;
  setSelectedPath: (path: string) => void;
}>({ selectedPath: null, setSelectedPath: () => {} });

interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
  isFile: boolean;
}

export interface CodePanelProps {
  projectId: string;
  selectedPath: string | null;
  onPathChange: (path: string | null) => void;
  width: number;
  isOpen: boolean;
  onToggleOpen: () => void;
  onResizerMouseDown: () => void;
  isResizing?: boolean;
}

export function CodePanel({
  projectId,
  selectedPath,
  onPathChange,
  width,
  isOpen,
  onToggleOpen,
  onResizerMouseDown,
  isResizing = false,
}: CodePanelProps) {
  const [treeOpen, setTreeOpen] = useState(true);
  const value = {
    selectedPath,
    setSelectedPath: (p: string) => onPathChange(p),
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={onToggleOpen}
        className="shrink-0 w-8 border-r border-[var(--border)] border-opacity-60 bg-[var(--bg)] py-4 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
        title="Show code viewer"
        aria-label="Show code viewer"
      >
        →
      </button>
    );
  }

  return (
    <>
      <section
        className="flex shrink-0 flex-col border-r border-[var(--border)] border-opacity-60 bg-[var(--bg)]"
        style={{ width, minWidth: 200, maxWidth: 800 }}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] border-opacity-60 px-2 py-1">
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => setTreeOpen((o) => !o)}
              className="rounded p-1 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
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
            onClick={onToggleOpen}
            className="rounded p-1 text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
            title="Collapse code viewer"
            aria-label="Collapse code viewer"
          >
            ←
          </button>
        </div>
        <div className="flex flex-1 min-h-0">
          <FileSelectionContext.Provider value={value}>
            {treeOpen ? (
              <>
                <FileTree projectId={projectId} />
                <FileViewer projectId={projectId} />
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setTreeOpen(true)}
                  className="shrink-0 w-6 border-r border-[var(--border)] border-opacity-40 bg-[var(--bg)] text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
                  title="Show file tree"
                  aria-label="Show file tree"
                >
                  ▶
                </button>
                <FileViewer projectId={projectId} />
              </>
            )}
          </FileSelectionContext.Provider>
        </div>
      </section>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
      <div
        role="separator"
        aria-orientation="vertical"
        onMouseDown={onResizerMouseDown}
        className={`shrink-0 w-2 cursor-col-resize border-r border-[var(--border)] border-opacity-60 bg-transparent hover:bg-[var(--accent)] hover:bg-opacity-20 ${isResizing ? 'bg-[var(--accent)] bg-opacity-30' : ''}`}
        title="Drag to resize code panel"
      />
    </>
  );
}

function FileTree({ projectId }: { projectId: string }) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/project/${projectId}/tree`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data) {
          setTree(data);
          const topDirs = (data.children ?? [])
            .filter((c: TreeNode) => !c.isFile && c.path)
            .map((c: TreeNode) => c.path);
          setOpenDirs((prev) => {
            const next = new Set(prev);
            topDirs.forEach((p: string) => next.add(p));
            return next;
          });
        }
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

  const topLevel = tree.children ?? [];
  return (
    <div className="w-36 shrink-0 overflow-y-auto border-r border-[var(--border)] border-opacity-40 py-0.5 font-mono text-[11px]">
      {topLevel.map((node) => (
        <TreeNodes
          key={node.path}
          node={node}
          openDirs={openDirs}
          onToggle={toggle}
          depth={0}
        />
      ))}
    </div>
  );
}

function TreeNodes({
  node,
  openDirs,
  onToggle,
  depth,
}: {
  node: TreeNode;
  openDirs: Set<string>;
  onToggle: (path: string) => void;
  depth: number;
}) {
  const { selectedPath: effectiveSelected } = useContext(FileSelectionContext);
  const isOpen = openDirs.has(node.path);
  const hasChildren = node.children && node.children.length > 0;

  if (node.isFile) {
    return (
      <FileItem
        path={node.path}
        name={node.name}
        depth={depth}
        selected={effectiveSelected === node.path}
      />
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => hasChildren && onToggle(node.path)}
        className="flex w-full items-center gap-0.5 py-0.5 pr-1 text-left hover:bg-[var(--card)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-0"
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
              openDirs={openDirs}
              onToggle={onToggle}
              depth={depth + 1}
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
      className={`flex w-full items-center gap-0.5 py-0.5 pr-1 text-left hover:bg-[var(--card)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-0 ${selected ? 'bg-[var(--card)] text-[var(--accent)]' : ''}`}
      style={{ paddingLeft: `${depth * 8 + 6}px` }}
    >
      <span className="w-3 shrink-0" />
      <span className="truncate text-[11px]">{name}</span>
    </button>
  );
}

function FileViewer({ projectId }: { projectId: string }) {
  const { theme } = useTheme();
  const { selectedPath } = useContext(FileSelectionContext);
  const [content, setContent] = useState<string | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPath) {
      setContent(null);
      setHtml(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(
      `/api/project/${projectId}/file?path=${encodeURIComponent(selectedPath)}&highlight=1&theme=${theme}`
    )
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data?.error || !data?.content) {
          setError(data?.error || 'File not found');
          setContent(null);
          setHtml(null);
        } else {
          setContent(data.content);
          setHtml(data.html ?? null);
          setError(null);
        }
      })
      .catch(() => {
        setError('Could not load file');
        setContent(null);
        setHtml(null);
      })
      .finally(() => setLoading(false));
  }, [projectId, selectedPath, theme]);

  if (!selectedPath) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
        <p className="text-[11px] text-[var(--muted)] opacity-80">
          Select a file from the tree
        </p>
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

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
        <p className="text-[11px] text-[var(--error)]">{error}</p>
        <p className="text-[10px] text-[var(--muted)] truncate max-w-full">
          {selectedPath}
        </p>
      </div>
    );
  }

  const lines = (content ?? '').split(/\r?\n/);
  return (
    <div className="flex flex-1 flex-col min-w-0 min-h-0 overflow-hidden">
      <div className="shrink-0 border-b border-[var(--border)] border-opacity-40 px-2 py-1 text-[10px] text-[var(--muted)] truncate">
        {selectedPath}
      </div>
      <div className="flex-1 min-h-0 overflow-auto bg-[var(--bg)]">
        {html ? (
          <div
            className="text-sm min-h-full p-2 font-mono text-[11px] leading-snug [&_pre]:m-0 [&_pre]:p-0 [&_pre]:!bg-transparent [&_pre]:!border-0 [&_pre]:min-h-full [&_pre]:whitespace-pre-wrap [&_pre]:break-words [&_code]:block [&_code]:min-w-0"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        ) : (
          <pre className="min-h-full font-mono text-[11px] leading-snug text-[var(--text)] p-2 whitespace-pre-wrap break-words">
            <code>
              {lines.map((line, i) => (
                <div key={i} className="table-row">
                  <span className="table-cell w-6 select-none pr-2 text-right text-[var(--muted)] opacity-70 align-top">
                    {i + 1}
                  </span>
                  <span className="table-cell whitespace-pre-wrap break-words">
                    {line || ' '}
                  </span>
                </div>
              ))}
            </code>
          </pre>
        )}
      </div>
    </div>
  );
}
