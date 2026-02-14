import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const WORKSPACES_DIR = path.join(process.cwd(), 'workspaces');

export async function GET() {
  try {
    if (!fs.existsSync(WORKSPACES_DIR)) {
      return NextResponse.json({ projects: [] });
    }
    const dirs = fs.readdirSync(WORKSPACES_DIR, { withFileTypes: true });
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
