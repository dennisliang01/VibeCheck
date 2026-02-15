import { NextResponse } from 'next/server';
import { loadProjectMap } from '@/lib/storage';
import { GENERAL_CATEGORIES, topicToGeneralCategories } from '@/lib/questionCategories';

const MAX_CATEGORIES = 6;

/**
 * GET /api/project/[id]/question/categories
 * Returns up to 6 general 2-word categories that have matching topics.
 */
export async function GET(
  _req: Request,
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

    const hasTopic = new Set<string>();
    for (const t of projectMap.topics) {
      for (const cat of topicToGeneralCategories(t.title, t.description, t.id)) {
        hasTopic.add(cat);
      }
    }
    let categories = GENERAL_CATEGORIES.filter((c) => hasTopic.has(c)).slice(0, MAX_CATEGORIES);
    if (categories.length === 0) categories = ['Utilities'];

    return NextResponse.json({ categories });
  } catch (e) {
    console.error('Categories API error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to load categories' },
      { status: 500 }
    );
  }
}
