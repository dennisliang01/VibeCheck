import { NextRequest, NextResponse } from 'next/server';
import { getLLMClient } from '@/lib/llm';
import { loadProjectMap, loadLearnerModel, loadSessionHistory } from '@/lib/storage';
import type { ProjectMapTopic } from '@/lib/schemas';

const CATEGORIES = ['UI', 'Functionality', 'Performance', 'Data & state', 'Security', 'General'] as const;
export type QuestionCategory = (typeof CATEGORIES)[number];

/** Map project topic to a high-level category (UI, Functionality, Performance, etc.). */
function topicToCategory(topic: ProjectMapTopic | null, topicId: string): QuestionCategory {
  const text = topic
    ? `${topic.title} ${topic.description} ${topic.id}`.toLowerCase()
    : topicId.toLowerCase();
  if (/\b(ui|component|layout|view|render|style|css)\b/.test(text)) return 'UI';
  if (/\b(performance|optim|speed|memory|cache)\b/.test(text)) return 'Performance';
  if (/\b(data|state|schema|model|store|database|api)\b/.test(text)) return 'Data & state';
  if (/\b(auth|security|login|permission|token)\b/.test(text)) return 'Security';
  if (/\b(entry|setup|route|flow|logic|function|handler)\b/.test(text)) return 'Functionality';
  return 'General';
}

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
    const topic = projectMap.topics.find((t) => t.id === question.topicId) ?? null;
    const category = topicToCategory(topic, question.topicId);
    const fileHints = topic?.fileHints;
    return NextResponse.json({ ...question, category, fileHints });
  } catch (e) {
    console.error('Generate question error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to generate question' },
      { status: 500 }
    );
  }
}
