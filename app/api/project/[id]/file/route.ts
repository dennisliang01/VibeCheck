import { NextRequest, NextResponse } from 'next/server';
import { getFile } from '@/lib/workspace';
import { highlightCode } from '@/lib/highlight';

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
    const highlight = req.nextUrl.searchParams.get('highlight') === '1';
    const html = highlight ? await highlightCode(content, pathParam) : undefined;
    return NextResponse.json({
      path: pathParam,
      content,
      ...(html !== undefined && { html }),
    });
  } catch (e) {
    console.error('Get file error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'File not found' },
      { status: 500 }
    );
  }
}
