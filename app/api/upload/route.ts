import { NextRequest, NextResponse } from 'next/server';
import AdmZip from 'adm-zip';
import path from 'path';
import fs from 'fs';
import { ensureWorkspacesDir } from '@/lib/workspace';
import { extractZipToProjectDir, generateProjectId, getZipEntriesForBlob } from '@/lib/zipExtract';
import { isBlobStorageAvailable, blobPutProjectFile } from '@/lib/blobStorage';

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

    if (process.env.VERCEL) {
      if (!isBlobStorageAvailable()) {
        return NextResponse.json(
          {
            error:
              'Persistent storage is required on Vercel. In your Vercel project: go to Storage → Create Blob store and connect it. Ensure the store’s token is enabled for Preview (and Production). Then redeploy.',
          },
          { status: 503 }
        );
      }
      const entries = getZipEntriesForBlob(zip);
      if (entries.length === 0) {
        return NextResponse.json(
          { error: 'Zip contains no valid files (e.g. only __MACOSX or empty). Add at least one file to the zip.' },
          { status: 400 }
        );
      }
      for (const { relativePath, data } of entries) {
        await blobPutProjectFile(projectId, relativePath, data);
      }
      return NextResponse.json({
        projectId,
        message: 'Project uploaded successfully',
      });
    }

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
