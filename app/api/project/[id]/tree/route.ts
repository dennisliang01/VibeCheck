import { NextRequest, NextResponse } from 'next/server';
import { repoTreeAsync } from '@/lib/workspace';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const tree = await repoTreeAsync(projectId);
    return NextResponse.json(tree);
  } catch (e) {
    console.error('Tree error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to get tree' },
      { status: 500 }
    );
  }
}
