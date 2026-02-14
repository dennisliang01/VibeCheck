import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import AdmZip from 'adm-zip';
import { ensureWorkspacesDir } from '@/lib/workspace';
import { extractZipToProjectDir, generateProjectId } from '@/lib/zipExtract';

const SAMPLE_ZIP_PATH = path.join(process.cwd(), 'examples', 'sample.zip');

export async function POST() {
  try {
    if (!fs.existsSync(SAMPLE_ZIP_PATH)) {
      return NextResponse.json(
        { error: 'Sample project not found. Run: npm run create-sample-zip' },
        { status: 404 }
      );
    }

    const buffer = fs.readFileSync(SAMPLE_ZIP_PATH);
    const zip = new AdmZip(buffer);
    const projectId = generateProjectId();
    const workspacesDir = ensureWorkspacesDir();
    const projectDir = path.join(workspacesDir, projectId);
    fs.mkdirSync(projectDir, { recursive: true });

    extractZipToProjectDir(zip, projectDir);

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
