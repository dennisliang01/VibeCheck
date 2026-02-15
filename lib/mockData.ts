import type { ValidationReport } from './schemas';

/**
 * Mock validation data used when Python backend is not yet integrated.
 * API route will try to read from workspace JSON first, then fall back here.
 */
export function getMockValidationReport(_projectId: string): ValidationReport {
  return {
    scores: {
      performance: 72,
      security: 85,
      codeQuality: 68,
      architecture: 78,
    },
    feedback: [
      {
        id: 'fb-1',
        title: 'Consider memoizing expensive computations',
        severity: 'medium',
        filePath: 'src/app.ts',
        recommendation: 'Use React.memo or useMemo for components/functions that recompute on every render.',
      },
      {
        id: 'fb-2',
        title: 'Add input validation',
        severity: 'high',
        filePath: 'src/utils/format.ts',
        recommendation: 'Validate and sanitize user inputs before processing to prevent injection attacks.',
      },
      {
        id: 'fb-3',
        title: 'Extract duplicated logic',
        severity: 'low',
        recommendation: 'Refactor repeated patterns into shared utilities to improve maintainability.',
      },
    ],
  };
}
