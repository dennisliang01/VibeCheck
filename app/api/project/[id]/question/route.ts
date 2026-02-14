import { NextRequest, NextResponse } from 'next/server';
import { getLLMClient } from '@/lib/llm';
import { loadProjectMap, loadLearnerModel, loadSessionHistory } from '@/lib/storage';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const projectMap = loadProjectMap(projectId);
    if (!projectMap) {
      return NextResponse.json(
        { error: 'Build project map first (POST /api/project/[id]/map)' },
        { status: 400 }
      );
    }
    const learnerModel = loadLearnerModel();
    const history = loadSessionHistory(projectId);
    const client = getLLMClient();
    const question = await client.generateQuestion(
      projectMap,
      learnerModel,
      history.entries
    );
    return NextResponse.json(question);
  } catch (e) {
    console.error('Generate question error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to generate question' },
      { status: 500 }
    );
  }
}
