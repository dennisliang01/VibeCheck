import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getWorkspaceDir } from '@/lib/workspace';
import { ValidationReportSchema } from '@/lib/schemas';
import { getMockValidationReport } from '@/lib/mockData';
import { codevalToValidationReport } from '@/lib/codevalReport';

/**
 * GET /api/project/[id]/validation
 * Returns validation scores and feedback.
 * Reads validation_report.json from workspace (codeval output), transforms to UI format.
 * Falls back to mock data if no report exists.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;

    try {
      const workspaceDir = getWorkspaceDir(projectId);
      const reportPath = path.join(workspaceDir, 'validation_report.json');
      const debugPath = path.join(workspaceDir, 'validation_debug.json');
      if (fs.existsSync(reportPath)) {
        const raw = fs.readFileSync(reportPath, 'utf-8');
        const parsed = JSON.parse(raw);
        const report = codevalToValidationReport(parsed);
        const validated = ValidationReportSchema.parse(report);
        // Write debug JSON for troubleshooting
        try {
          fs.writeFileSync(
            debugPath,
            JSON.stringify(
              {
                _debug: {
                  source: 'codeval',
                  rawPath: 'validation_report.json',
                  transformedAt: new Date().toISOString(),
                  scoreSource: 'Backend/codeval/orchestrator.py _compute_scores_from_clusters',
                },
                raw: parsed,
                transformed: validated,
              },
              null,
              2
            ),
            'utf-8'
          );
        } catch {
          // ignore debug write failures
        }
        return NextResponse.json(validated);
      }
    } catch (e) {
      console.warn('Validation report parse error:', e);
      // Fall through to mock data
    }

    const report = getMockValidationReport(projectId);
    return NextResponse.json(report);
  } catch (e) {
    console.error('Validation API error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load validation' },
      { status: 500 }
    );
  }
}
