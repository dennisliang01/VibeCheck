'use client';

import { useEffect, useState, useCallback } from 'react';
import { ValidationSectionCard } from './ValidationSectionCard';
import { useWorkspace } from '@/components/workspace/WorkspaceContext';
import type { ValidationReport, ValidationSection, ValidationSectionDetail } from '@/lib/schemas';

type ValidationStatus = 'idle' | 'running' | 'done' | 'error';

interface ValidationPanelProps {
  projectId: string;
}

function severityColor(severity?: string): string {
  switch (severity) {
    case 'critical': return 'text-[var(--error)]';
    case 'high': return 'text-[var(--error)]';
    case 'medium': return 'text-[var(--muted)]';
    case 'low': return 'text-[var(--muted)]';
    default: return 'text-[var(--muted)]';
  }
}

function DetailRow({ detail, onOpenCode }: { detail: ValidationSectionDetail; onOpenCode?: (p: string) => void }) {
  const location = detail.line != null ? `${detail.file}:${detail.line}` : detail.file;
  const hasLocation = Boolean(detail.file);

  return (
    <li className="rounded border border-[var(--border)] bg-[var(--bg)] p-3">
      <p className="text-sm text-[var(--text)]">{detail.description}</p>
      {detail.suggestion && (
        <p className="mt-1 text-xs text-[var(--muted)]">{detail.suggestion}</p>
      )}
      {hasLocation && (
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-xs font-mono text-[var(--muted)]">{location}</span>
          {onOpenCode && (
            <button
              type="button"
              onClick={() => onOpenCode(detail.file)}
              className="shrink-0 rounded border border-[var(--border)] px-2 py-1 text-xs font-medium text-[var(--accent)] hover:bg-[var(--accent)] hover:bg-opacity-10 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
              aria-label={`Open ${detail.file} in code panel`}
            >
              Open code
            </button>
          )}
        </div>
      )}
      {detail.severity && (
        <p className={`mt-1 text-xs capitalize ${severityColor(detail.severity)}`}>
          Severity: {detail.severity}
        </p>
      )}
    </li>
  );
}

const SECTION_LABELS: Record<string, string> = {
  functional: 'Functional',
  security: 'Security',
  resilience: 'Resilience',
  performance: 'Performance',
  quality: 'Quality',
  dependency: 'Dependency',
  documentation: 'Documentation',
  architecture: 'Architecture',
  concurrency: 'Concurrency',
  api_contract: 'API Contract',
};

const CODEVAL_IDS = [
  'functional',
  'security',
  'resilience',
  'performance',
  'quality',
  'dependency',
  'documentation',
  'architecture',
  'concurrency',
  'api_contract',
] as const;

function buildSectionsFromLegacy(report: ValidationReport): ValidationSection[] {
  const scores = (report.scores ?? {}) as Record<string, number>;
  const feedback = report.feedback ?? [];
  const legacyFallback = Math.round(
    (Number(scores.performance) + Number(scores.security) + Number(scores.codeQuality) + Number(scores.architecture)) / 4 || 0
  );
  const details = feedback.map((f) => ({
    file: f.filePath ?? '',
    line: undefined as number | undefined,
    description: f.title,
    severity: f.severity as 'critical' | 'high' | 'medium' | 'low',
    suggestion: f.recommendation,
  }));

  return CODEVAL_IDS.map((id) => ({
    id,
    label: SECTION_LABELS[id] ?? id.replace(/_/g, ' '),
    score: Math.round(Number(scores[id]) || legacyFallback),
    details: details.length ? details : [],
  }));
}

const POLL_MS = 2000;

export function ValidationPanel({ projectId }: ValidationPanelProps) {
  const { onOpenCode } = useWorkspace();
  const [data, setData] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<ValidationStatus>('idle');
  const [statusError, setStatusError] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<ValidationSection | null>(null);

  const fetchReport = useCallback(() => {
    fetch(`/api/project/${projectId}/validation`)
      .then((res) => (res.ok ? res.json() : null))
      .then((d) => {
        if (d) setData(d);
      });
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      if (cancelled) return;
      const res = await fetch(`/api/project/${projectId}/validation/status`);
      const s = await res.json();
      if (cancelled) return;
      setStatus(s.status ?? 'idle');
      setStatusError(s.message ?? null);
      if (s.status === 'done') {
        fetchReport();
        setLoading(false);
        return;
      }
      if (s.status === 'error') {
        setLoading(false);
        return;
      }
      if (s.status === 'running') {
        setLoading(false);
      }
      if (s.status === 'idle' || s.status === 'running') {
        pollTimer = setTimeout(poll, POLL_MS);
      }
    }

    setLoading(true);
    poll();
    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [projectId, fetchReport]);

  useEffect(() => {
    if (status === 'done' && !data) fetchReport();
  }, [status, data, fetchReport]);

  if (loading && status !== 'running') {
    return <p className="text-[var(--muted)]">Loading validation…</p>;
  }

  if (status === 'running') {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6">
          <div className="flex items-center gap-4">
            <div
              className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]"
              aria-hidden
            />
            <div>
              <p className="text-sm font-medium text-[var(--text)]">
                Code validation in progress
              </p>
              <p className="text-xs text-[var(--muted)]">
                Running codeval agents (functional, security, performance, etc.)
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border-2 border-[var(--error)] bg-[var(--card)] p-4">
          <p className="text-sm font-medium text-[var(--error)]">
            Validation failed
          </p>
          {statusError && (
            <p className="mt-1 text-xs text-[var(--muted)]">{statusError}</p>
          )}
        </div>
      </div>
    );
  }

  if (status === 'done' && !data) {
    return <p className="text-[var(--muted)]">Loading results…</p>;
  }

  if (!data) {
    return <p className="text-[var(--muted)]">Could not load validation data.</p>;
  }

  const sections = data.sections?.length
    ? data.sections
    : buildSectionsFromLegacy(data);

  return (
    <div className="space-y-6 w-full max-w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sections.map((section) => (
          <ValidationSectionCard
            key={section.id}
            section={section}
            selected={selectedSection?.id === section.id}
            onSelect={() => setSelectedSection((prev) => (prev?.id === section.id ? null : section))}
          />
        ))}
      </div>
      {selectedSection && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
          <h3 className="text-sm font-medium text-[var(--text)] mb-3">{selectedSection.label} — details</h3>
          {selectedSection.details.length > 0 ? (
            <>
              <p className="mb-2 text-xs font-medium text-[var(--muted)] uppercase tracking-wider">
                Lines to review
              </p>
              <ul className="space-y-2">
                {selectedSection.details.map((d, i) => (
                  <DetailRow key={i} detail={d} onOpenCode={onOpenCode} />
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-[var(--muted)]">No specific findings for this section.</p>
          )}
        </div>
      )}
    </div>
  );
}
