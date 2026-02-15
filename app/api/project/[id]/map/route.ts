import { NextRequest, NextResponse } from 'next/server';
import { getLLMClient } from '@/lib/llm';
import { loadProjectMapAsync, saveProjectMapAsync } from '@/lib/storage';
import { buildProjectContextAsync, deriveProjectNameFallbackAsync } from '@/lib/buildProjectMapSkill';
import { ProjectMapSchema } from '@/lib/schemas';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const existing = await loadProjectMapAsync(projectId);
    if (existing) {
      return NextResponse.json(existing);
    }
    return NextResponse.json(
      { error: 'Project map not built yet. POST to build.' },
      { status: 404 }
    );
  } catch (e) {
    console.error('Get map error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to get map' },
      { status: 500 }
    );
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const body = await req.json().catch(() => ({}));
    const projectName = (body.name as string) || projectId;

    const existing = await loadProjectMapAsync(projectId);
    if (existing) {
      return NextResponse.json(existing);
    }

    const context = await buildProjectContextAsync(projectId, projectName);
    context.projectId = projectId;
    const client = getLLMClient();
    const raw = await client.buildProjectMap(context);
    raw.projectId = projectId;
    raw.name = await deriveProjectNameFallbackAsync(
      projectId,
      context.fileList ?? [],
      raw.name ?? ''
    );
    const map = ProjectMapSchema.parse(raw);
    await saveProjectMapAsync(projectId, map);

    return NextResponse.json(map);
  } catch (e) {
    console.error('Build map error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to build map' },
      { status: 500 }
    );
  }
}
