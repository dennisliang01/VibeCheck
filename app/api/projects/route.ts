import { NextResponse } from 'next/server';
import fs from 'fs';
import { getWorkspacesDirPath } from '@/lib/workspace';

export async function GET() {
  try {
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
