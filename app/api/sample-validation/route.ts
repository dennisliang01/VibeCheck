import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { codevalToValidationReport } from '@/lib/codevalReport';
import { ValidationReportSchema } from '@/lib/schemas';
import { getMockValidationReport } from '@/lib/mockData';

/** Serves validation report for the sample project from examples/test_sample/validation_report_demo.json */
const TEST_SAMPLE_REPORT_PATH = path.join(process.cwd(), 'examples', 'test_sample', 'validation_report_demo.json');
const FALLBACK_REPORT_PATH = path.join(process.cwd(), 'examples', 'validation_report_demo.json');

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const reportPath = fs.existsSync(TEST_SAMPLE_REPORT_PATH)
      ? TEST_SAMPLE_REPORT_PATH
      : fs.existsSync(FALLBACK_REPORT_PATH)
        ? FALLBACK_REPORT_PATH
        : null;

    if (reportPath) {
      const raw = fs.readFileSync(reportPath, 'utf-8');
      const parsed = JSON.parse(raw);
      const report = codevalToValidationReport(parsed);
      const validated = ValidationReportSchema.parse(report);
      return NextResponse.json(validated);
    }

    return NextResponse.json(getMockValidationReport('sample'));
  } catch (e) {
    console.error('Sample validation error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load sample validation' },
      { status: 500 }
    );
  }
}
