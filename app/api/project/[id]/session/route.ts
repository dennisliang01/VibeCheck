import { NextRequest, NextResponse } from 'next/server';
import { loadSessionHistoryAsync } from '@/lib/storage';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const history = await loadSessionHistoryAsync(projectId);
    return NextResponse.json(history);
  } catch (e) {
    console.error('Session error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load session' },
      { status: 500 }
    );
  }
}
