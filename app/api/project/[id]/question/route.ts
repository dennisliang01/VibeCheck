import { NextRequest, NextResponse } from 'next/server';
import { getLLMClient } from '@/lib/llm';
import { loadProjectMapAsync, loadLearnerModelAsync, loadSessionHistoryAsync } from '@/lib/storage';
import type { ProjectMapTopic } from '@/lib/schemas';
import { topicToGeneralCategories, isGeneralCategory } from '@/lib/questionCategories';

/** Filter topics to those matching the general category. */
function filterTopicsByCategory(
  projectMap: { topics: ProjectMapTopic[] },
  category: string
): ProjectMapTopic[] {
  if (!isGeneralCategory(category)) return projectMap.topics;
  return projectMap.topics.filter((t) =>
    topicToGeneralCategories(t.title, t.description, t.id).includes(category)
  );
}

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const categoryParam = req.nextUrl.searchParams.get('category');
    const category = categoryParam?.trim() || null;

    const projectMap = await loadProjectMapAsync(projectId);
    if (!projectMap) {
      return NextResponse.json(
        { error: 'Build project map first (POST /api/project/[id]/map)' },
        { status: 400 }
      );
    }

    let mapForQuestion = projectMap;
    if (category) {
      const filtered = filterTopicsByCategory(projectMap, category);
      if (filtered.length > 0) {
        mapForQuestion = { ...projectMap, topics: filtered };
      }
    }

    const learnerModel = await loadLearnerModelAsync();
    const history = await loadSessionHistoryAsync(projectId);
    const client = getLLMClient();
    const question = await client.generateQuestion(
      mapForQuestion,
      learnerModel,
      history.entries,
      category ?? undefined
    );
    const topic = projectMap.topics.find((t) => t.id === question.topicId) ?? null;
    const categories = topic
      ? topicToGeneralCategories(topic.title, topic.description, topic.id)
      : [];
    const fileHints = topic?.fileHints;
    return NextResponse.json({ ...question, categories, fileHints });
  } catch (e) {
    console.error('Generate question error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to generate question' },
      { status: 500 }
    );
  }
}
