import { createHighlighter } from 'shiki';

/** Supported languages. Only load these to keep bundle light. */
const LANGS = [
  'typescript',
  'tsx',
  'javascript',
  'jsx',
  'json',
  'python',
  'java',
  'sql',
  'go',
  'c',
  'cpp',
  'rust',
  'markdown',
  'bash',
  'plaintext',
] as const;

/** Cached highlighter instance. Reused across requests (no per-request recreation). */
let highlighterPromise: ReturnType<typeof createHighlighter> | null = null;

async function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({
      themes: ['github-dark'],
      langs: [...LANGS],
    });
  }
  return highlighterPromise;
}

/**
 * Detect Shiki language from file path extension.
 * Falls back to "plaintext" for unsupported extensions.
 */
export function detectLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'ts':
      return 'typescript';
    case 'tsx':
      return 'tsx';
    case 'js':
      return 'javascript';
    case 'jsx':
      return 'jsx';
    case 'json':
      return 'json';
    case 'py':
      return 'python';
    case 'java':
      return 'java';
    case 'sql':
      return 'sql';
    case 'go':
      return 'go';
    case 'c':
      return 'c';
    case 'cpp':
      return 'cpp';
    case 'h':
      return 'c';
    case 'hpp':
      return 'cpp';
    case 'rs':
      return 'rust';
    case 'md':
      return 'markdown';
    case 'sh':
      return 'bash';
    default:
      return 'plaintext';
  }
}

/**
 * Highlight code with Shiki (server-side).
 * Uses github-dark theme. Caches the highlighter globally.
 */
export async function highlightCode(code: string, filePath: string): Promise<string> {
  const lang = detectLanguage(filePath);
  const safeLang = LANGS.includes(lang as (typeof LANGS)[number]) ? lang : 'plaintext';
  const highlighter = await getHighlighter();
  return highlighter.codeToHtml(code, {
    lang: safeLang,
    theme: 'github-dark',
  });
}
