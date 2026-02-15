'use client';

import { useCallback, useEffect, useRef } from 'react';

export type TabId = 'understanding' | 'validation';

interface TabsProps {
  value: TabId;
  onChange: (value: TabId) => void;
  tabs: { id: TabId; label: string }[];
}

export function Tabs({ value, onChange, tabs }: TabsProps) {
  const tabListRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, currentIndex: number) => {
      if (e.key === 'ArrowLeft' && currentIndex > 0) {
        e.preventDefault();
        onChange(tabs[currentIndex - 1].id);
        const prev = tabListRef.current?.querySelector(`[data-tab-index="${currentIndex - 1}"]`);
        if (prev instanceof HTMLElement) prev.focus();
      } else if (e.key === 'ArrowRight' && currentIndex < tabs.length - 1) {
        e.preventDefault();
        onChange(tabs[currentIndex + 1].id);
        const next = tabListRef.current?.querySelector(`[data-tab-index="${currentIndex + 1}"]`);
        if (next instanceof HTMLElement) next.focus();
      }
    },
    [onChange, tabs]
  );

  return (
    <div
      ref={tabListRef}
      role="tablist"
      aria-label="Project workspace tabs"
      className="flex items-end gap-0"
    >
      {tabs.map((tab, index) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={value === tab.id}
          aria-controls={`tabpanel-${tab.id}`}
          id={`tab-${tab.id}`}
          data-tab-index={index}
          tabIndex={value === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          className={`relative px-5 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded-t-md border border-b-0 border-[var(--border)] ${
            value === tab.id
              ? 'bg-[var(--card)] text-[var(--text)] -mb-px z-10'
              : 'bg-[var(--border)]/50 text-[var(--muted)] hover:bg-[var(--border)]/70 hover:text-[var(--text)]'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
