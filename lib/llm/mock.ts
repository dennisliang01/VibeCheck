import type { LLMClient } from './types';
import type { ProjectMap, ProjectMapTopic, QuestionObj, GradeObj, LearnerModel } from '@/lib/schemas';
import type { SessionEntry } from '@/lib/schemas';
import type { ProjectContext } from './types';
import type { QuestionCategory } from '@/lib/questionCategories';
import { deriveProjectNameFallback } from '@/lib/buildProjectMapSkill';

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

function buildQuestionFromCategory(
  category: QuestionCategory | undefined,
  topic: ProjectMapTopic,
  fileHint: string | undefined,
  historyLen: number
): { question: string; expectedTraits: string[] } {
  const filePart = fileHint ? ` Open the file ${fileHint} to help you.` : '';
  const templates = category
    ? getCategoryTemplates(category)
    : getAllTemplates();
  const template = templates[historyLen % templates.length];
  return template(topic, fileHint);
}

type QuestionTemplateFn = (t: ProjectMapTopic, f: string | undefined) => { question: string; expectedTraits: string[] };

function getCategoryTemplates(category: QuestionCategory): QuestionTemplateFn[] {
  const base: QuestionTemplateFn = (t, f) => ({
    question: `In one or two sentences: what does the file ${f || 'that starts the app'} do?${f ? ` Open ${f}.` : ''}`,
    expectedTraits: [t.title.toLowerCase(), 'file', 'job', 'do'],
  });
  const byCategory: Partial<Record<QuestionCategory, QuestionTemplateFn[]>> = {
    UI: [
      (t, f) => ({ question: `What UI component or layout does the file ${f || 'a component file'} render? Describe what the user sees.${f ? ` Open ${f}.` : ''}`, expectedTraits: ['component', 'render', 'ui', 'layout', 'view'] }),
      (t, f) => ({ question: `Which component handles user interaction (e.g. button click, form submit)? What happens when the user does that?${f ? ` Check ${f}.` : ''}`, expectedTraits: ['handler', 'click', 'event', 'interaction'] }),
      (t, f) => ({ question: `How is styling applied to the UI in ${f || 'the component files'}? (CSS, Tailwind, inline styles?)${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['style', 'css', 'class', 'tailwind'] }),
    ],
    Functionality: [
      (t, f) => ({ question: `When the app starts, what is the first file that runs, and what does it do next? List the steps in order.${f ? ` Open ${f}.` : ''}`, expectedTraits: ['first', 'file', 'step', 'order', 'run', 'start'] }),
      (t, f) => ({ question: `If you deleted or broke the code in ${f || 'one of the main files'}, which other files might stop working? Name 1–2 specific files.${f ? ` Check ${f}.` : ''}`, expectedTraits: ['file', 'depend', 'import', 'break'] }),
      (t, f) => ({ question: `You see an error when the app starts. Which file should you open first to find the problem?${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['file', 'open', 'error', 'start'] }),
    ],
    Performance: [
      (t, f) => ({ question: `Where might this app be slow or use a lot of memory? Look for loops, large data, or heavy work.${f ? ` Check ${f}.` : ''}`, expectedTraits: ['slow', 'loop', 'memory', 'performance', 'optim'] }),
      (t, f) => ({ question: `Does the app cache or reuse any data to avoid repeated work? If so, where?${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['cache', 'reuse', 'memo', 'store'] }),
      (t, f) => ({ question: `What could be optimized to make the app faster?${f ? ` Inspect ${f}.` : ''}`, expectedTraits: ['optim', 'fast', 'load', 'call'] }),
    ],
    'Data & state': [
      (t, f) => ({ question: `Where does the app store or manage data (state, database, API)? Describe the flow.${f ? ` Check ${f}.` : ''}`, expectedTraits: ['state', 'data', 'store', 'api', 'database'] }),
      (t, f) => ({ question: `How does data get from the backend or API to the UI? Trace one path.${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['fetch', 'api', 'data', 'flow'] }),
      (t, f) => ({ question: `What schema or structure does the data have? Where is it defined?${f ? ` Inspect ${f}.` : ''}`, expectedTraits: ['schema', 'model', 'type', 'structure'] }),
    ],
    Security: [
      (t, f) => ({ question: `Where does the app handle authentication (login, tokens, sessions)?${f ? ` Check ${f}.` : ''}`, expectedTraits: ['auth', 'login', 'token', 'session'] }),
      (t, f) => ({ question: `How does the app validate or sanitize user input to prevent security issues?${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['validate', 'input', 'sanitize', 'security'] }),
      (t, f) => ({ question: `Where are permissions or access control checked?${f ? ` Inspect ${f}.` : ''}`, expectedTraits: ['permission', 'access', 'authorize', 'role'] }),
    ],
    General: [
      (t, f) => ({ question: `In one or two sentences: what does the file ${f || t.fileHints?.[0] || 'the main file'} do?${f ? ` Open ${f}.` : ''}`, expectedTraits: [t.title.toLowerCase(), 'file', 'job', 'do'] }),
      (t, f) => ({ question: `When the app starts, what runs first? List 1–2 key steps.${f ? ` Check ${f}.` : ''}`, expectedTraits: ['first', 'start', 'run', 'step'] }),
      (t, f) => ({ question: `Which file would you open to fix a bug in ${t.title.toLowerCase()}? Why?${f ? ` Hint: ${f}.` : ''}`, expectedTraits: ['file', 'fix', 'bug', 'open'] }),
    ],
  };
  return byCategory[category] ?? [base];
}

function getAllTemplates(): QuestionTemplateFn[] {
  return [
    (t, f) => ({ question: `When the app starts, what is the first file that runs, and what does it do next? List the steps in order.${f ? ` Open ${f} to help.` : ''}`, expectedTraits: ['first', 'file', 'step', 'order', 'run', 'start'] }),
    (t, f) => ({ question: `If you deleted or broke the code in ${f || 'one of the main files'}, which other files might stop working? Name 1–2 specific files.${f ? ` Check ${f}.` : ''}`, expectedTraits: ['file', 'depend', 'import', 'break'] }),
    (t, f) => ({ question: `You see an error when the app starts. Which file should you open first to find the problem?${f ? ` Look at ${f}.` : ''}`, expectedTraits: ['file', 'open', 'error', 'start'] }),
    (t, f) => ({ question: `In one or two sentences: what does the file ${f || 'that starts the app'} do? (What is its job?)${f ? ` Open ${f}.` : ''}`, expectedTraits: [t.title.toLowerCase(), 'file', 'job', 'do'] }),
  ];
}

export class MockLLMClient implements LLMClient {
  async buildProjectMap(context: ProjectContext): Promise<ProjectMap> {
    const rawName = context.name || 'Sample Project';
    const name = deriveProjectNameFallback(
      context.projectId ?? '',
      context.fileList ?? [],
      rawName
    );
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
    history: SessionEntry[],
    category?: string
  ): Promise<QuestionObj> {
    const topic = pickTopic(projectMap, learnerModel, history);
    const fileHint = topic.fileHints?.[0];
    const { question, expectedTraits } = buildQuestionFromCategory(
      category as QuestionCategory | undefined,
      topic,
      fileHint,
      history.length
    );
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

    /** Fuzzy match: tolerant of spelling, partial words. No penalty for typos or fragments. */
    function traitsMatch(ans: string, trait: string): boolean {
      const t = trait.toLowerCase();
      if (ans.includes(t)) return true;
      for (const w of ans.split(/\s+/)) {
        if (!w) continue;
        if (w.includes(t) || t.includes(w)) return true;
        if (t.length >= 4 && w.length >= 3 && t.slice(0, 3) === w.slice(0, 3) && Math.abs(t.length - w.length) <= 2)
          return true;
      }
      return false;
    }

    for (const trait of expectedTraits) {
      if (traitsMatch(answer, trait)) {
        matched.push(trait);
      } else {
        missed.push(trait);
      }
    }
    const ratio = expectedTraits.length > 0 ? matched.length / expectedTraits.length : 0.5;
    const score = Math.round(Math.min(100, Math.max(0, ratio * 90)));

    const feedbackParts: string[] = [];
    if (matched.length > 0) {
      feedbackParts.push(`You touched on: ${matched.slice(0, 3).join(', ')}.`);
    }
    if (missed.length > 0) {
      feedbackParts.push(`Consider adding: ${missed.slice(0, 3).join(', ')}.`);
    }
    if (feedbackParts.length === 0 && answer.length < 10) {
      feedbackParts.push('Try adding a bit more—any relevant keywords or file names help.');
    }
    const feedback = feedbackParts.length > 0 ? feedbackParts.join(' ') : 'Good; try to reference specific files or flow when you can.';

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
