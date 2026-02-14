import { NextRequest, NextResponse } from 'next/server';
import { getFile } from '@/lib/workspace';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const pathParam = req.nextUrl.searchParams.get('path');
    if (!pathParam) {
      return NextResponse.json(
        { error: 'Query param "path" is required' },
        { status: 400 }
      );
    }
    const content = getFile(projectId, pathParam);
    return NextResponse.json({ path: pathParam, content });
  } catch (e) {
    console.error('Get file error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'File not found' },
      { status: 500 }
    );
  }
}
