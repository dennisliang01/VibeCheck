import type { LLMClient } from './types';
import type { ProjectMap, ProjectMapTopic, QuestionObj, GradeObj, LearnerModel } from '@/lib/schemas';
import type { SessionEntry } from '@/lib/schemas';
import type { ProjectContext } from './types';

const QUESTION_TEMPLATES = [
  'trace_flow',
  'change_impact',
  'debug_location',
] as const;

type QuestionTemplate = (typeof QUESTION_TEMPLATES)[number];

function pickTopic(
  projectMap: ProjectMap,
  learnerModel: LearnerModel,
  history: SessionEntry[]
): ProjectMapTopic {
  const learningTopics = projectMap.topics;
  if (learningTopics.length === 0) throw new Error('Project map has no topics');
  const mastered = new Set(learnerModel.topicMasteries.filter((m) => m.score >= 70).map((m) => m.topicId));
  const weak = learningTopics.filter((t) => !mastered.has(t.id));
  const pool = weak.length > 0 ? weak : learningTopics;
  const idx = history.length % pool.length;
  return pool[idx];
}

function buildQuestionFromTemplate(
  template: QuestionTemplate,
  topic: ProjectMapTopic,
  fileHint: string | undefined
): { question: string; expectedTraits: string[] } {
  const filePart = fileHint ? ` Open the file ${fileHint} to help you.` : '';
  switch (template) {
    case 'trace_flow':
      return {
        question: `When the app starts, what is the first file that runs, and what does it do next? List the steps in order (e.g. "First X runs, then it calls Y").${filePart}`,
        expectedTraits: ['first', 'file', 'step', 'order', 'run', 'call', 'import', 'start', topic.title.toLowerCase()],
      };
    case 'change_impact':
      return {
        question: `If you deleted or broke the code in ${fileHint || 'one of the main files'}, which other files might stop working? Name 1–2 specific file names and why they depend on it.${filePart}`,
        expectedTraits: ['file', 'depend', 'import', 'break', 'use', 'call', topic.title.toLowerCase()],
      };
    case 'debug_location':
      return {
        question: `You see an error when the app starts. Which file should you open first to find the problem, and what would you look for in that file?${filePart}`,
        expectedTraits: ['file', 'open', 'look', 'error', 'start', 'code', topic.title.toLowerCase()],
      };
    default:
      return {
        question: `In one or two sentences: what does the file ${fileHint || 'that starts the app'} do? (What is its job?)${filePart}`,
        expectedTraits: [topic.title.toLowerCase(), 'file', 'job', 'do', 'start'],
      };
  }
}

export class MockLLMClient implements LLMClient {
  async buildProjectMap(context: ProjectContext): Promise<ProjectMap> {
    const name = context.name || 'Sample Project';
    const fileList = context.fileList ?? [];
    const keyPaths = context.keyFiles?.map((f) => f.path) ?? [];
    const hints = keyPaths.length > 0 ? keyPaths : fileList;
    const now = new Date().toISOString();
    return {
      projectId: '', // caller will set
      name,
      summary: `A mock project map for ${name} with ${context.fileCount} files. Key areas: entry point, components, and utilities.`,
      topics: [
        {
          id: 'topic-entry',
          title: 'Entry point and app setup',
          description: 'How the application boots and routes are configured.',
          fileHints: hints.filter((f) => f.includes('index') || f.includes('main') || f.includes('app')).slice(0, 3) || hints.slice(0, 2),
        },
        {
          id: 'topic-components',
          title: 'Components and UI',
          description: 'Reusable UI components and their structure.',
          fileHints: hints.filter((f) => f.includes('component') || f.endsWith('.tsx')).slice(0, 5) || hints.slice(0, 2),
        },
        {
          id: 'topic-utils',
          title: 'Utilities and helpers',
          description: 'Shared logic and helper functions.',
          fileHints: hints.filter((f) => f.includes('util') || f.includes('lib')).slice(0, 3) || hints.slice(0, 2),
        },
      ],
      builtAt: now,
    };
  }

  async generateQuestion(
    projectMap: ProjectMap,
    learnerModel: LearnerModel,
    history: SessionEntry[]
  ): Promise<QuestionObj> {
    const topic = pickTopic(projectMap, learnerModel, history);
    const template: QuestionTemplate = QUESTION_TEMPLATES[history.length % QUESTION_TEMPLATES.length];
    const fileHint = topic.fileHints?.[0];
    const { question, expectedTraits } = buildQuestionFromTemplate(template, topic, fileHint);
    const qNum = history.length + 1;
    const id = `q-${topic.id}-${qNum}-${Date.now()}`;
    return {
      id,
      topicId: topic.id,
      question,
      hint: fileHint ? `Check ${fileHint}` : undefined,
      expectedConcepts: expectedTraits,
    };
  }

  async gradeAnswer(
    questionObj: QuestionObj,
    userAnswer: string,
    projectMap: ProjectMap
  ): Promise<GradeObj> {
    const answer = (userAnswer || '').trim().toLowerCase();
    const expectedTraits = questionObj.expectedConcepts ?? [];
    const matched: string[] = [];
    const missed: string[] = [];
    for (const trait of expectedTraits) {
      const lower = trait.toLowerCase();
      if (answer.includes(lower) || answer.split(/\s+/).some((w) => w.includes(lower) || lower.includes(w))) {
        matched.push(trait);
      } else {
        missed.push(trait);
      }
    }
    const ratio = expectedTraits.length > 0 ? matched.length / expectedTraits.length : 0.5;
    const wordBonus = Math.min(20, (answer.split(/\s+/).length || 0) * 2);
    const score = Math.round(Math.min(100, Math.max(0, ratio * 70 + wordBonus)));

    const feedbackParts: string[] = [];
    if (matched.length > 0) {
      feedbackParts.push(`You touched on: ${matched.slice(0, 3).join(', ')}.`);
    }
    if (missed.length > 0) {
      feedbackParts.push(`Add more about: ${missed.slice(0, 3).join(', ')} to strengthen your answer.`);
    }
    if (feedbackParts.length === 0 && answer.length < 20) {
      feedbackParts.push('Give a more specific answer with file names or steps where possible.');
    }
    const feedback = feedbackParts.length > 0 ? feedbackParts.join(' ') : 'Good engagement; try to reference specific files or flow next time.';

    const topic = projectMap.topics.find((t) => t.id === questionObj.topicId);
    const topicIndex = projectMap.topics.findIndex((t) => t.id === questionObj.topicId);
    const nextTopic = projectMap.topics[(topicIndex + 1) % projectMap.topics.length];

    return {
      score,
      feedback,
      correctPoints: matched.length > 0 ? matched.slice(0, 5).map((m) => `Mentioned: ${m}`) : undefined,
      missedPoints: missed.length > 0 ? missed.slice(0, 5).map((m) => `Consider adding: ${m}`) : undefined,
      nextRecommendedTopicId: score >= 70 ? nextTopic?.id : topic?.id,
    };
  }
}

export const mockLLMClient = new MockLLMClient();
