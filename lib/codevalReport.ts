/**
 * Transforms codeval JSON output to the ValidationReport schema used by the UI.
 */

import type {
  ValidationReport,
  ValidationSection,
  ValidationSectionDetail,
} from './schemas';

export interface CodevalReport {
  summary?: string;
  scores?: {
    categories?: Record<string, number>;
    overall?: number;
  };
  findings?: Array<{
    id: string;
    severity: string;
    confidence?: number;
    title: string;
    evidence?: {
      file?: string;
      lines?: number[];
      snippet?: string;
    };
    impact?: string;
    recommendation?: string;
    patch_hint?: string;
    test_hint?: string;
    source?: string;
  }>;
  clusters?: Array<{
    cluster_id?: string;
    primary_finding_id?: string;
    consolidated_title?: string;
    consolidated_severity?: string;
    consolidated_impact?: string;
    consolidated_recommendation?: string;
    category?: string;
    related_finding_ids?: string[];
  }>;
  all_findings?: Array<{
    id: string;
    severity: string;
    title: string;
    evidence?: { file?: string; lines?: number[] };
    impact?: string;
    recommendation?: string;
    source?: string;
  }>;
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

function roundScore(v: number): number {
  if (v < 0) return 0;
  if (v > 100) return 100;
  return Math.round(v);
}

/**
 * Convert codeval JSON report to ValidationReport for the UI.
 */
export function codevalToValidationReport(raw: CodevalReport): ValidationReport {
  const categories = raw.scores?.categories ?? {};
  const clusters = raw.clusters ?? [];
  const findings = raw.all_findings ?? raw.findings ?? [];
  const findingMap = new Map(findings.map((f) => [f.id, f]));

  // Build sections from codeval categories
  const sectionIds = [
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
  ];

  const sections: ValidationSection[] = sectionIds.map((id) => {
    const score = categories[id];
    const numScore = typeof score === 'number' ? roundScore(score) : 0;
    const details: ValidationSectionDetail[] = [];

    // Add details from clusters in this category
    for (const c of clusters) {
      if ((c.category ?? 'functional') !== id) continue;
      const primary = c.primary_finding_id
        ? findingMap.get(c.primary_finding_id)
        : null;
      const file = primary?.evidence?.file ?? '';
      const line = primary?.evidence?.lines?.[0];
      details.push({
        file,
        line,
        description: c.consolidated_title ?? primary?.title ?? 'Issue',
        severity: (c.consolidated_severity as 'critical' | 'high' | 'medium' | 'low') ?? 'medium',
        suggestion: c.consolidated_recommendation ?? primary?.recommendation,
      });
    }

    return {
      id,
      label: SECTION_LABELS[id] ?? id.replace(/_/g, ' '),
      score: numScore,
      details,
    };
  });

  // Scores: all codeval categories
  const scores: Record<string, number> = {};
  for (const id of sectionIds) {
    scores[id] = roundScore(categories[id] ?? 0);
  }

  // Feedback from top findings (for legacy consumers)
  const feedback = (raw.findings ?? [])
    .slice(0, 10)
    .map((f, i) => ({
      id: f.id || `fb-${i}`,
      title: f.title,
      severity: (f.severity === 'critical' ? 'high' : f.severity) as 'high' | 'medium' | 'low',
      filePath: f.evidence?.file,
      recommendation: f.recommendation ?? '',
    }));

  return {
    scores,
    feedback,
    sections,
  };
}
