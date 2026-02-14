import { NextRequest, NextResponse } from 'next/server';
import { loadSessionHistory } from '@/lib/storage';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const history = loadSessionHistory(projectId);
    return NextResponse.json(history);
  } catch (e) {
    console.error('Session error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load session' },
      { status: 500 }
    );
  }
}
