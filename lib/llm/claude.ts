import type { LLMClient } from './types';
import type { ProjectMap, QuestionObj, GradeObj, LearnerModel } from '@/lib/schemas';
import type { SessionEntry } from '@/lib/schemas';
import type { ProjectContext } from './types';
import { ProjectMapSchema, QuestionObjSchema, GradeObjSchema } from '@/lib/schemas';

const API_URL = 'https://api.anthropic.com/v1/messages';

function getApiKey(): string {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY is not set');
  return key;
}

function extractJsonBlock(text: string): string {
  const match = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (match) return match[1].trim();
  const start = text.indexOf('{');
  if (start === -1) return text;
  let depth = 0;
  let end = start;
  for (let i = start; i < text.length; i++) {
    if (text[i] === '{') depth++;
    if (text[i] === '}') {
      depth--;
      if (depth === 0) {
        end = i + 1;
        break;
      }
    }
  }
  return text.slice(start, end);
}

const DEFAULT_MODEL = 'claude-sonnet-4-20250514';

async function callClaude(system: string, user: string): Promise<string> {
  const model = process.env.ANTHROPIC_MODEL || DEFAULT_MODEL;
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': getApiKey(),
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      max_tokens: 4096,
      system,
      messages: [{ role: 'user', content: user }],
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Claude API error: ${res.status} ${err}`);
  }
  const data = await res.json();
  const content = data.content?.[0]?.text ?? '';
  return content;
}

export class ClaudeLLMClient implements LLMClient {
  async buildProjectMap(context: ProjectContext): Promise<ProjectMap> {
    const system = `You are a coding coach. Output only valid JSON. No markdown, no explanation.`;
    const name = context.name || 'Unknown';
    let user = `Create a project map (JSON) for this codebase.
Project name: ${name}
- fileCount: ${context.fileCount}
- fileList (first 80): ${JSON.stringify(context.fileList.slice(0, 80))}
- extensions: ${JSON.stringify(context.extensions)}
`;
    if (context.keyFiles && context.keyFiles.length > 0) {
      user += `\nKey file contents (use these to ground the summary and topics):\n`;
      for (const k of context.keyFiles) {
        user += `\n--- ${k.path} ---\n${k.content}\n`;
      }
    }
    user += `\nRespond with a single JSON object (use projectId: "" as placeholder):
{
  "projectId": "",
  "name": "string",
  "summary": "string",
  "topics": [{"id": "string", "title": "string", "description": "string", "fileHints": ["path"]}],
  "builtAt": "ISO date string"
}`;
    const raw = await callClaude(system, user);
    const parsed = JSON.parse(extractJsonBlock(raw));
    parsed.builtAt = parsed.builtAt || new Date().toISOString();
    return ProjectMapSchema.parse(parsed);
  }

  async generateQuestion(
    projectMap: ProjectMap,
    learnerModel: LearnerModel,
    history: SessionEntry[]
  ): Promise<QuestionObj> {
    const system = `You are a coding coach for novice programmers. Output only valid JSON. No markdown.`;
    const user = `Project map: ${JSON.stringify(projectMap)}
Learner masteries: ${JSON.stringify(learnerModel.topicMasteries)}
Recent history (last 5): ${JSON.stringify(history.slice(-5))}

Generate ONE code-understanding question for a NOVICE programmer (beginner). Rules:
- Use simple, everyday words. Avoid jargon; if you use a term like "entry point" or "bootstrap", the question should make it clear what you mean.
- Be concrete: ask about specific file names, "what runs first", "what does this file do", "which file would you open to fix X".
- Prefer topics the learner has not mastered. Use topicId and fileHints from the project map.
- Keep the question short (1–2 sentences). Include a hint that names a specific file to look at when possible.
Output JSON: {"id": "unique-id", "topicId": "from map", "question": "string", "hint": "optional file path or short hint", "expectedConcepts": ["string"]}`;
    const raw = await callClaude(system, user);
    const parsed = JSON.parse(extractJsonBlock(raw));
    return QuestionObjSchema.parse(parsed);
  }

  async gradeAnswer(
    questionObj: QuestionObj,
    userAnswer: string,
    projectMap: ProjectMap
  ): Promise<GradeObj> {
    const system = `You are a coding coach. Output only valid JSON.`;
    const user = `Question: ${JSON.stringify(questionObj)}
User answer: ${userAnswer}
Project map: ${JSON.stringify(projectMap)}

Grade the answer (0-100) and give brief feedback. Output JSON:
{"score": number, "feedback": "string", "correctPoints": ["string"], "missedPoints": ["string"], "nextRecommendedTopicId": "optional topic id"}`;
    const raw = await callClaude(system, user);
    const parsed = JSON.parse(extractJsonBlock(raw));
    return GradeObjSchema.parse(parsed);
  }
}

export const claudeLLMClient = new ClaudeLLMClient();
