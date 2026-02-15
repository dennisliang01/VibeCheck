import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getWorkspaceDir } from '@/lib/workspace';
import { ValidationReportSchema } from '@/lib/schemas';
import { getMockValidationReport } from '@/lib/mockData';

/**
 * GET /api/project/[id]/validation
 * Returns validation scores and feedback.
 * Phase 1: Returns mock data.
 * Phase 2: Will try to read workspaces/[id]/validation_report.json from Python output first.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;

    // Phase 2: Try reading Python-generated JSON from workspace
    try {
      const workspaceDir = getWorkspaceDir(projectId);
      const reportPath = path.join(workspaceDir, 'validation_report.json');
      if (fs.existsSync(reportPath)) {
        const raw = fs.readFileSync(reportPath, 'utf-8');
        const parsed = JSON.parse(raw);
        const report = ValidationReportSchema.parse(parsed);
        return NextResponse.json(report);
      }
    } catch {
      // Fall through to mock data
    }

    // Phase 1: Mock data until Python integration is ready
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
