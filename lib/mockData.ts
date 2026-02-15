import type { ValidationReport, ValidationSection } from './schemas';

const DEFAULT_SECTIONS: ValidationSection[] = [
  { id: 'functional', label: 'Functional Validator', score: 82, details: [{ file: 'src/api/handlers.ts', line: 42, description: 'Missing input validation on request body', severity: 'high', suggestion: 'Add schema validation using Zod or similar.' }] },
  { id: 'logic', label: 'Logical Inspector', score: 78, details: [{ file: 'src/utils/parser.ts', line: 17, description: 'Edge case not handled when input is empty', severity: 'medium', suggestion: 'Add early return for empty input.' }] },
  { id: 'architecture', label: 'Structural Architect', score: 85, details: [{ file: 'src/services/index.ts', line: 8, description: 'Consider extracting service initialization to factory', severity: 'low', suggestion: 'Use dependency injection for testability.' }] },
  { id: 'technical_debt', label: 'Tech Debt Checker', score: 68, details: [{ file: 'src/app.ts', line: 92, description: 'Duplicate logic detected', severity: 'medium', suggestion: 'Extract into shared utility.' }, { file: 'src/legacy/module.ts', line: 15, description: 'Unused variable', severity: 'low', suggestion: 'Remove or prefix with underscore.' }] },
  { id: 'performance', label: 'Performance Expert', score: 72, details: [{ file: 'src/components/List.tsx', line: 28, description: 'Expensive recomputation on each render', severity: 'medium', suggestion: 'Use React.memo or useMemo.' }] },
  { id: 'security', label: 'Security Auditor', score: 85, details: [{ file: 'src/utils/format.ts', line: 12, description: 'User input used without sanitization', severity: 'high', suggestion: 'Validate and sanitize before processing.' }] },
  { id: 'observability', label: 'Log Verifier', score: 70, details: [{ file: 'src/api/routes.ts', line: 56, description: 'Error path lacks structured logging', severity: 'medium', suggestion: 'Add structured log with context.' }] },
  { id: 'resilience', label: 'Error Manager', score: 75, details: [{ file: 'src/services/fetch.ts', line: 33, description: 'Network error not caught', severity: 'high', suggestion: 'Add try/catch and retry logic.' }] },
];

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
      { id: 'fb-1', title: 'Consider memoizing expensive computations', severity: 'medium', filePath: 'src/app.ts', recommendation: 'Use React.memo or useMemo for components/functions that recompute on every render.' },
      { id: 'fb-2', title: 'Add input validation', severity: 'high', filePath: 'src/utils/format.ts', recommendation: 'Validate and sanitize user inputs before processing to prevent injection attacks.' },
      { id: 'fb-3', title: 'Extract duplicated logic', severity: 'low', recommendation: 'Refactor repeated patterns into shared utilities to improve maintainability.' },
    ],
    sections: DEFAULT_SECTIONS,
  };
}
