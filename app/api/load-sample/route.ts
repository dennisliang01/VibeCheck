import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import AdmZip from 'adm-zip';
import { ensureWorkspacesDir } from '@/lib/workspace';
import { extractZipToProjectDir, generateProjectId, getZipEntriesForBlob } from '@/lib/zipExtract';
import { isBlobStorageAvailable, blobPutProjectFile } from '@/lib/blobStorage';

/** Sample is always from examples: test_sample.zip or examples/test_sample/ folder. */
const EXAMPLES_DIR = path.join(process.cwd(), 'examples');
const SAMPLE_ZIP_PATH = path.join(EXAMPLES_DIR, 'test_sample.zip');
const SAMPLE_FOLDER_PATH = path.join(EXAMPLES_DIR, 'test_sample', 'test_sample');
/** Validation for sample: prefer examples/test_sample/validation_report_demo.json */
const TEST_SAMPLE_VALIDATION_PATH = path.join(EXAMPLES_DIR, 'test_sample', 'validation_report_demo.json');
const VALIDATION_REPORT_PATH = path.join(EXAMPLES_DIR, 'validation_report.json');
const DEMO_VALIDATION_REPORT_PATH = path.join(EXAMPLES_DIR, 'validation_report_demo.json');
const BACKEND_REPORT_PATH = path.join(process.cwd(), 'Backend', 'report.json');

function getSampleValidationReportPath(): string | null {
  if (fs.existsSync(TEST_SAMPLE_VALIDATION_PATH)) return TEST_SAMPLE_VALIDATION_PATH;
  if (fs.existsSync(BACKEND_REPORT_PATH)) return BACKEND_REPORT_PATH;
  if (fs.existsSync(VALIDATION_REPORT_PATH)) return VALIDATION_REPORT_PATH;
  if (fs.existsSync(DEMO_VALIDATION_REPORT_PATH)) return DEMO_VALIDATION_REPORT_PATH;
  return null;
}

export async function POST() {
  try {
    let zipPath = SAMPLE_ZIP_PATH;
    if (!fs.existsSync(zipPath) && fs.existsSync(SAMPLE_FOLDER_PATH)) {
      const zip = new AdmZip();
      const addDir = (dir: string, prefix = '') => {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const e of entries) {
          const full = path.join(dir, e.name);
          const name = prefix ? `${prefix}/${e.name}` : e.name;
          if (e.isDirectory()) addDir(full, name);
          else zip.addFile(name.replace(/\\/g, '/'), fs.readFileSync(full));
        }
      };
      addDir(SAMPLE_FOLDER_PATH);
      zipPath = path.join(EXAMPLES_DIR, 'test_sample_temp.zip');
      zip.writeZip(zipPath);
    }
    if (!fs.existsSync(zipPath)) {
      return NextResponse.json(
        {
          error:
            'Sample not found. Add examples/test_sample.zip (run: npm run create-test-sample-zip) or ensure examples/test_sample/test_sample/ exists.',
        },
        { status: 404 }
      );
    }

    const buffer = fs.readFileSync(zipPath);
    const zip = new AdmZip(buffer);
    const projectId = generateProjectId();

    if (process.env.VERCEL) {
      if (!isBlobStorageAvailable()) {
        return NextResponse.json(
          {
            error:
              'Persistent storage is required on Vercel. In your Vercel project: go to Storage → Create Blob store and connect it. Ensure the store\'s token is enabled for Preview (and Production). Then redeploy.',
          },
          { status: 503 }
        );
      }
      const entries = getZipEntriesForBlob(zip);
      for (const { relativePath, data } of entries) {
        await blobPutProjectFile(projectId, relativePath, data);
      }
      const reportPath = getSampleValidationReportPath();
      if (reportPath) {
        const reportContent = fs.readFileSync(reportPath, 'utf-8');
        await blobPutProjectFile(projectId, 'validation_report.json', reportContent);
      }
      return NextResponse.json({
        projectId,
        message: 'Sample project loaded',
      });
    }

    const workspacesDir = ensureWorkspacesDir();
    const projectDir = path.join(workspacesDir, projectId);
    fs.mkdirSync(projectDir, { recursive: true });
    extractZipToProjectDir(zip, projectDir);
    const reportPath = getSampleValidationReportPath();
    if (reportPath) {
      fs.copyFileSync(reportPath, path.join(projectDir, 'validation_report.json'));
    }

    return NextResponse.json({
      projectId,
      message: 'Sample project loaded',
    });
  } catch (e) {
    console.error('Load sample error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load sample' },
      { status: 500 }
    );
  }
}
