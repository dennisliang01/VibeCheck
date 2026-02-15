import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getWorkspaceDir } from '@/lib/workspace';
import { ValidationReportSchema, type ValidationReport } from '@/lib/schemas';
import { getMockValidationReport } from '@/lib/mockData';
import { codevalToValidationReport } from '@/lib/codevalReport';
import { isBlobStorageAvailable, blobGetProjectFileContent } from '@/lib/blobStorage';

export const dynamic = 'force-dynamic';

const DEMO_REPORT_PATH = path.join(process.cwd(), 'examples', 'validation_report_demo.json');

/**
 * GET /api/project/[id]/validation
 * Returns validation scores and feedback.
 * 1. Reads validation_report.json from workspace/Blob if present (from zip or codeval run).
 * 2. Else loads pre-generated demo report from examples/validation_report_demo.json (for demo / test_sample).
 * 3. Else returns mock data.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;

    const tryDemoReport = (): ValidationReport | null => {
      try {
        if (fs.existsSync(DEMO_REPORT_PATH)) {
          const raw = fs.readFileSync(DEMO_REPORT_PATH, 'utf-8');
          const parsed = JSON.parse(raw);
          const report = codevalToValidationReport(parsed);
          return ValidationReportSchema.parse(report);
        }
      } catch {
        // ignore
      }
      return null;
    };

    if (process.env.VERCEL && isBlobStorageAvailable()) {
      try {
        const raw = await blobGetProjectFileContent(projectId, 'validation_report.json');
        const parsed = JSON.parse(raw);
        const report = codevalToValidationReport(parsed);
        const validated = ValidationReportSchema.parse(report);
        return NextResponse.json(validated);
      } catch {
        // Fall through to demo or mock
      }
      const demo = tryDemoReport();
      if (demo) return NextResponse.json(demo);
      return NextResponse.json(getMockValidationReport(projectId));
    }

    try {
      const workspaceDir = getWorkspaceDir(projectId);
      const reportPath = path.join(workspaceDir, 'validation_report.json');
      const debugPath = path.join(workspaceDir, 'validation_debug.json');
      if (fs.existsSync(reportPath)) {
        const raw = fs.readFileSync(reportPath, 'utf-8');
        const parsed = JSON.parse(raw);
        const report = codevalToValidationReport(parsed);
        const validated = ValidationReportSchema.parse(report);
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
          // ignore
        }
        return NextResponse.json(validated);
      }
    } catch (e) {
      console.warn('Validation report parse error:', e);
    }

    const demo = tryDemoReport();
    if (demo) return NextResponse.json(demo);
    return NextResponse.json(getMockValidationReport(projectId));
  } catch (e) {
    console.error('Validation API error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load validation' },
      { status: 500 }
    );
  }
}
