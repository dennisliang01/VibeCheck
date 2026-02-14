import { NextRequest, NextResponse } from 'next/server';
import { getLLMClient } from '@/lib/llm';
import {
  loadProjectMap,
  appendSessionEntry,
  updateLearnerModelFromGrade,
} from '@/lib/storage';
import { QuestionObjSchema } from '@/lib/schemas';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const body = await req.json();
    const questionObj = QuestionObjSchema.parse(body.questionObj);
    const userAnswer = String(body.userAnswer ?? '').trim();

    const projectMap = loadProjectMap(projectId);
    if (!projectMap) {
      return NextResponse.json(
        { error: 'Project map not found' },
        { status: 400 }
      );
    }

    const client = getLLMClient();
    const grade = await client.gradeAnswer(
      questionObj,
      userAnswer,
      projectMap
    );

    const now = new Date().toISOString();
    appendSessionEntry(projectId, {
      questionId: questionObj.id,
      topicId: questionObj.topicId,
      question: questionObj.question,
      userAnswer,
      score: grade.score,
      feedback: grade.feedback,
      answeredAt: now,
    });

    updateLearnerModelFromGrade(questionObj.topicId, grade.score);

    return NextResponse.json({
      grade,
      nextRecommendedTopicId: grade.nextRecommendedTopicId,
    });
  } catch (e) {
    console.error('Grade error:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Failed to grade' },
      { status: 500 }
    );
  }
}
