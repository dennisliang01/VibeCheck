import type { LLMClient } from './types';
import { mockLLMClient } from './mock';
import { claudeLLMClient } from './claude';

export type { LLMClient, FilesSummary, ProjectContext } from './types';
export { MockLLMClient, mockLLMClient } from './mock';
export { ClaudeLLMClient, claudeLLMClient } from './claude';

export function getLLMClient(): LLMClient {
  if (process.env.USE_CLAUDE_LLM === 'true' && process.env.ANTHROPIC_API_KEY) {
    return claudeLLMClient;
  }
  return mockLLMClient;
}
