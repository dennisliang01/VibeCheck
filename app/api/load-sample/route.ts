import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import AdmZip from 'adm-zip';
import { ensureWorkspacesDir } from '@/lib/workspace';
import { extractZipToProjectDir, generateProjectId } from '@/lib/zipExtract';

const SAMPLE_ZIP_PATH = path.join(process.cwd(), 'examples', 'test_sample.zip');
const SAMPLE_SRC_FALLBACK = path.join(process.cwd(), 'examples', 'test_sample', 'test_sample');

export async function POST() {
  try {
    let zipPath = SAMPLE_ZIP_PATH;
    if (!fs.existsSync(zipPath) && fs.existsSync(SAMPLE_SRC_FALLBACK)) {
      zipPath = path.join(process.cwd(), 'examples', 'test_sample_temp.zip');
      const zip = new AdmZip();
      function addDir(dir: string, prefix = '') {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const e of entries) {
          const full = path.join(dir, e.name);
          const name = prefix ? `${prefix}/${e.name}` : e.name;
          if (e.isDirectory()) addDir(full, name);
          else zip.addFile(name.replace(/\\/g, '/'), fs.readFileSync(full));
        }
      }
      addDir(SAMPLE_SRC_FALLBACK);
      zip.writeZip(zipPath);
    }
    if (!fs.existsSync(zipPath)) {
      return NextResponse.json(
        { error: 'Sample project not found. Run: npm run create-test-sample-zip' },
        { status: 404 }
      );
    }

    const buffer = fs.readFileSync(zipPath);
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
