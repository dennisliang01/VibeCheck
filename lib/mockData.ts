import type { ValidationReport, ValidationSection } from './schemas';

const DEFAULT_SECTIONS: ValidationSection[] = [
  { id: 'functional', label: 'Functional', score: 82, details: [{ file: 'src/api/handlers.ts', line: 42, description: 'Missing input validation on request body', severity: 'high', suggestion: 'Add schema validation using Zod or similar.' }] },
  { id: 'security', label: 'Security', score: 85, details: [{ file: 'src/utils/format.ts', line: 12, description: 'User input used without sanitization', severity: 'high', suggestion: 'Validate and sanitize before processing.' }] },
  { id: 'resilience', label: 'Resilience', score: 75, details: [{ file: 'src/services/fetch.ts', line: 33, description: 'Network error not caught', severity: 'high', suggestion: 'Add try/catch and retry logic.' }] },
  { id: 'performance', label: 'Performance', score: 72, details: [{ file: 'src/components/List.tsx', line: 28, description: 'Expensive recomputation on each render', severity: 'medium', suggestion: 'Use React.memo or useMemo.' }] },
  { id: 'quality', label: 'Quality', score: 68, details: [{ file: 'src/app.ts', line: 92, description: 'Duplicate logic detected', severity: 'medium', suggestion: 'Extract into shared utility.' }] },
  { id: 'dependency', label: 'Dependency', score: 70, details: [] },
  { id: 'documentation', label: 'Documentation', score: 78, details: [] },
  { id: 'architecture', label: 'Architecture', score: 85, details: [{ file: 'src/services/index.ts', line: 8, description: 'Consider extracting service initialization to factory', severity: 'low', suggestion: 'Use dependency injection for testability.' }] },
  { id: 'concurrency', label: 'Concurrency', score: 80, details: [] },
  { id: 'api_contract', label: 'API Contract', score: 76, details: [] },
];

/**
 * Mock validation data used when Python backend is not yet integrated.
 * API route will try to read from workspace JSON first, then fall back here.
 */
export function getMockValidationReport(_projectId: string): ValidationReport {
  return {
    scores: {
      functional: 82,
      security: 85,
      resilience: 75,
      performance: 72,
      quality: 68,
      dependency: 70,
      documentation: 78,
      architecture: 85,
      concurrency: 80,
      api_contract: 76,
    },
    feedback: [
      { id: 'fb-1', title: 'Consider memoizing expensive computations', severity: 'medium', filePath: 'src/app.ts', recommendation: 'Use React.memo or useMemo for components/functions that recompute on every render.' },
      { id: 'fb-2', title: 'Add input validation', severity: 'high', filePath: 'src/utils/format.ts', recommendation: 'Validate and sanitize user inputs before processing to prevent injection attacks.' },
      { id: 'fb-3', title: 'Extract duplicated logic', severity: 'low', recommendation: 'Refactor repeated patterns into shared utilities to improve maintainability.' },
    ],
    sections: DEFAULT_SECTIONS,
  };
}
