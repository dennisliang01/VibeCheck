import { NextRequest, NextResponse } from 'next/server';
import { searchRepoAsync } from '@/lib/workspace';

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const query = req.nextUrl.searchParams.get('q') ?? '';
    if (!query.trim()) {
      return NextResponse.json(
        { error: 'Query param "q" is required' },
        { status: 400 }
      );
    }
    const results = await searchRepoAsync(projectId, query);
    return NextResponse.json({ results });
  } catch (e) {
    console.error('Search error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Search failed' },
      { status: 500 }
    );
  }
}
