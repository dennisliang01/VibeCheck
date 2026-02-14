import type { TreeNode } from './workspace';
import { repoTree, searchRepo, getFile } from './workspace';
import { buildFilesSummary } from './filesSummary';
import type { ProjectContext } from './llm/types';

// Set number of key files to 6 to limit the context window for the LLM
const MAX_KEY_FILES = 6;
const MAX_CHARS_PER_FILE = 8000;

/** Flatten tree to list of file paths relative to project root (omit root node name). */
function flattenTreeToPaths(node: TreeNode, prefix = '', isRoot = false): string[] {
  if (node.isFile) {
    const path = prefix ? `${prefix}/${node.name}` : node.name;
    return [path];
  }
  const out: string[] = [];
  for (const c of node.children ?? []) {
    const nextPrefix = isRoot ? c.name : (prefix ? `${prefix}/${node.name}` : node.name);
    out.push(...flattenTreeToPaths(c, nextPrefix, false));
  }
  return out;
}

/** Score path for "entrypoint" (higher = more likely). */
function isEntrypoint(p: string): boolean {
  const lower = p.toLowerCase();
  const name = lower.split('/').pop() ?? lower;
  if (name === 'index.ts' || name === 'index.js' || name === 'index.tsx' || name === 'main.ts' || name === 'main.js') return true;
  if (name === 'app.tsx' || name === 'app.ts' || name === 'app.jsx' || name === 'app.js') return true;
  if (name === 'layout.tsx' || name === 'layout.ts') return true;
  if (lower.includes('/src/') && (name === 'index.' || name.startsWith('main.'))) return true;
  return false;
}

function isReadme(p: string): boolean {
  const name = (p.split('/').pop() ?? '').toLowerCase();
  return name.startsWith('readme');
}

function isRoute(p: string): boolean {
  const lower = p.toLowerCase();
  return lower.includes('route') || lower.includes('router') || (lower.includes('pages') && (lower.endsWith('.tsx') || lower.endsWith('.ts')));
}

function isDataOrSchema(p: string): boolean {
  const lower = p.toLowerCase();
  return lower.includes('schema') || lower.includes('model') || lower.includes('database') || lower.includes('db/') || lower.includes('/data/');
}

function isAuth(p: string): boolean {
  const lower = p.toLowerCase();
  return lower.includes('auth') || lower.includes('login') || lower.includes('session');
}

/**
 * Discover up to 6 key file paths: README, entrypoint, router, data/schema, auth, one core module.
 * Uses repo_tree + search_repo + fileList name matching.
 */
export function discoverKeyFilePaths(projectId: string): string[] {
  const tree = repoTree(projectId);
  const allPaths = flattenTreeToPaths(tree, '', true);
  const filesSummary = buildFilesSummary(projectId);
  const fileList = filesSummary.fileList.length > 0 ? filesSummary.fileList : allPaths;

  const searchQueries = ['README', 'main', 'entry', 'index', 'route', 'router', 'api', 'database', 'schema', 'model', 'auth', 'login'];
  const fromSearch = new Set<string>();
  for (const q of searchQueries) {
    const results = searchRepo(projectId, q);
    for (const r of results) {
      fromSearch.add(r.path);
    }
  }

  const readme = [...fileList, ...fromSearch].filter(isReadme)[0];
  const entrypoints = [...fileList, ...fromSearch].filter(isEntrypoint);
  const routes = [...fileList, ...fromSearch].filter(isRoute);
  const data = [...fileList, ...fromSearch].filter(isDataOrSchema);
  const auth = [...fileList, ...fromSearch].filter(isAuth);

  const picked = new Set<string>();
  if (readme) picked.add(readme);
  for (const p of entrypoints) {
    if (picked.size >= MAX_KEY_FILES) break;
    if (!picked.has(p)) picked.add(p);
  }
  for (const p of routes) {
    if (picked.size >= MAX_KEY_FILES) break;
    if (!picked.has(p)) picked.add(p);
  }
  for (const p of data) {
    if (picked.size >= MAX_KEY_FILES) break;
    if (!picked.has(p)) picked.add(p);
  }
  for (const p of auth) {
    if (picked.size >= MAX_KEY_FILES) break;
    if (!picked.has(p)) picked.add(p);
  }
  // One "core" module: first lib/ or components/ or app file not yet picked
  const coreCandidates = fileList.filter(
    (p) =>
      !picked.has(p) &&
      (p.includes('/lib/') || p.includes('/libs/') || p.includes('/components/') || p.includes('/app/') || p.includes('/core/'))
  );
  if (picked.size < MAX_KEY_FILES && coreCandidates[0]) picked.add(coreCandidates[0]);

  return Array.from(picked).slice(0, MAX_KEY_FILES);
}

/**
 * Read key files and return path + content (truncated).
 */
export function readKeyFiles(
  projectId: string,
  paths: string[],
  maxCharsPerFile = MAX_CHARS_PER_FILE
): Array<{ path: string; content: string }> {
  const out: Array<{ path: string; content: string }> = [];
  for (const p of paths) {
    try {
      let content = getFile(projectId, p);
      if (content.length > maxCharsPerFile) {
        content = content.slice(0, maxCharsPerFile) + '\n\n... (truncated)';
      }
      out.push({ path: p, content });
    } catch {
      // skip missing or unreadable
    }
  }
  return out;
}

/**
 * Build full project context: files summary + discovered key file paths + read contents.
 * Use this before calling LLM buildProjectMap.
 */
export function buildProjectContext(
  projectId: string,
  projectName?: string
): ProjectContext {
  const filesSummary = buildFilesSummary(projectId);
  const keyPaths = discoverKeyFilePaths(projectId);
  const keyFiles = readKeyFiles(projectId, keyPaths);

  return {
    projectId,
    name: projectName || projectId,
    fileCount: filesSummary.fileCount,
    fileList: filesSummary.fileList,
    totalSizeBytes: filesSummary.totalSizeBytes,
    extensions: filesSummary.extensions,
    keyFiles: keyFiles.length > 0 ? keyFiles : undefined,
  };
}
