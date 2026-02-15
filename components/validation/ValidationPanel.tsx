'use client';

import { useEffect, useState } from 'react';
import { ValidationSectionCard } from './ValidationSectionCard';
import { useWorkspace } from '@/components/workspace/WorkspaceContext';
import type { ValidationReport, ValidationSection, ValidationSectionDetail } from '@/lib/schemas';

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
  functional: 'Functional Validator',
  logic: 'Logical Inspector',
  architecture: 'Structural Architect',
  technical_debt: 'Tech Debt Checker',
  performance: 'Performance Expert',
  security: 'Security Auditor',
  observability: 'Log Verifier',
  resilience: 'Error Manager',
};

function buildSectionsFromLegacy(report: ValidationReport): ValidationSection[] {
  const scores = report.scores ?? {
    performance: 0,
    security: 0,
    codeQuality: 0,
    architecture: 0,
  };
  const feedback = report.feedback ?? [];
  const ids = ['functional', 'logic', 'architecture', 'technical_debt', 'performance', 'security', 'observability', 'resilience'] as const;
  const scoreMap: Record<string, number> = {
    functional: scores.codeQuality,
    logic: scores.architecture,
    architecture: scores.architecture,
    technical_debt: scores.codeQuality,
    performance: scores.performance,
    security: scores.security,
    observability: Math.round((scores.codeQuality + scores.architecture) / 2),
    resilience: Math.round((scores.codeQuality + scores.performance) / 2),
  };
  const details = feedback.map((f) => ({
    file: f.filePath ?? '',
    line: undefined as number | undefined,
    description: f.title,
    severity: f.severity as 'critical' | 'high' | 'medium' | 'low',
    suggestion: f.recommendation,
  }));

  return ids.map((id) => ({
    id,
    label: SECTION_LABELS[id] ?? id,
    score: scoreMap[id] ?? 0,
    details: id === 'technical_debt' ? details : [], // Legacy feedback lives under Tech Debt
  }));
}

export function ValidationPanel({ projectId }: ValidationPanelProps) {
  const { onOpenCode } = useWorkspace();
  const [data, setData] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSection, setSelectedSection] = useState<ValidationSection | null>(null);

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
