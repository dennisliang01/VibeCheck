import { NextRequest, NextResponse } from 'next/server';
import AdmZip from 'adm-zip';
import path from 'path';
import fs from 'fs';
import { ensureWorkspacesDir } from '@/lib/workspace';
import { extractZipToProjectDir, generateProjectId } from '@/lib/zipExtract';

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File | null;
    if (!file || !file.name.endsWith('.zip')) {
      return NextResponse.json(
        { error: 'Please upload a .zip file' },
        { status: 400 }
      );
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    if (buffer.length > MAX_SIZE_BYTES) {
      return NextResponse.json(
        { error: 'Zip file is too large (max 50MB)' },
        { status: 400 }
      );
    }

    const zip = new AdmZip(buffer);
    const projectId = generateProjectId();
    const workspacesDir = ensureWorkspacesDir();
    const projectDir = path.join(workspacesDir, projectId);
    fs.mkdirSync(projectDir, { recursive: true });

    extractZipToProjectDir(zip, projectDir);

    return NextResponse.json({
      projectId,
      message: 'Project uploaded successfully',
    });
  } catch (e) {
    console.error('Upload error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Upload failed' },
      { status: 500 }
    );
  }
}
