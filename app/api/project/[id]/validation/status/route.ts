import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { getWorkspaceDir } from '@/lib/workspace';
import { isBlobStorageAvailable, blobGetProjectFileContent } from '@/lib/blobStorage';

const STATUS_FILE = 'validation_status.json';

export const dynamic = 'force-dynamic';

/**
 * GET /api/project/[id]/validation/status
 * Returns current validation run status: idle, running, done, or error.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;

    if (process.env.VERCEL && isBlobStorageAvailable()) {
      try {
        const raw = await blobGetProjectFileContent(projectId, STATUS_FILE);
        const data = JSON.parse(raw);
        return NextResponse.json({
          status: data.status ?? 'idle',
          message: data.message,
          startedAt: data.startedAt,
          finishedAt: data.finishedAt,
        });
      } catch {
        return NextResponse.json({ status: 'idle' });
      }
    }

    const workspaceDir = getWorkspaceDir(projectId);
    const statusPath = path.join(workspaceDir, STATUS_FILE);
    if (!fs.existsSync(statusPath)) {
      return NextResponse.json({ status: 'idle' });
    }
    const raw = fs.readFileSync(statusPath, 'utf-8');
    const data = JSON.parse(raw);
    return NextResponse.json({
      status: data.status ?? 'idle',
      message: data.message,
      startedAt: data.startedAt,
      finishedAt: data.finishedAt,
    });
  } catch (e) {
    console.error('Validation status error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to get status' },
      { status: 500 }
    );
  }
}
