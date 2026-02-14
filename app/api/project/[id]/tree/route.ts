import { NextRequest, NextResponse } from 'next/server';
import { repoTree } from '@/lib/workspace';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const tree = repoTree(projectId);
    return NextResponse.json(tree);
  } catch (e) {
    console.error('Tree error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to get tree' },
      { status: 500 }
    );
  }
}
