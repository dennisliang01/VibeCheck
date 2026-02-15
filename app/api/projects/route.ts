import { NextResponse } from 'next/server';
import fs from 'fs';
import { getWorkspacesDirPath } from '@/lib/workspace';
import { isBlobStorageAvailable, blobListProjectIds } from '@/lib/blobStorage';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    if (process.env.VERCEL && isBlobStorageAvailable()) {
      const ids = await blobListProjectIds();
      const projects = ids.map((id) => ({ id, name: id }));
      return NextResponse.json({ projects });
    }
    const workspacesDir = getWorkspacesDirPath();
    if (!fs.existsSync(workspacesDir)) {
      return NextResponse.json({ projects: [] });
    }
    const dirs = fs.readdirSync(workspacesDir, { withFileTypes: true });
    const projects = dirs
      .filter((d) => d.isDirectory())
      .map((d) => ({
        id: d.name,
        name: d.name,
      }));
    return NextResponse.json({ projects });
  } catch (e) {
    console.error('List projects error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to list projects' },
      { status: 500 }
    );
  }
}
