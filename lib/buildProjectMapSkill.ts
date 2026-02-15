import fs from 'fs';
import path from 'path';
import type { TreeNode } from './workspace';
import { repoTree, searchRepo, getFile, getWorkspaceDir, getFileAsync, repoTreeAsync, searchRepoAsync } from './workspace';
import { buildFilesSummary, buildFilesSummaryAsync } from './filesSummary';
import type { ProjectContext } from './llm/types';
import { isBlobStorageAvailable } from './blobStorage';

/** Check if LLM name looks descriptive (not an ID). */
function isDescriptiveName(name: string, projectId: string): boolean {
  const t = name?.trim() ?? '';
  if (!t || t.length < 2) return false;
  if (t === projectId) return false;
  if (/^[a-f0-9-]{8,}$/i.test(t)) return false; // uuid/hex
  if (/^[a-z0-9]{12,}$/i.test(t) && !/\s/.test(t)) return false; // id-like
  return true;
}

/**
 * Fallback project name when LLM returns something non-descriptive.
 * Tries package.json "name", then top-level folder, then projectId.
 */
export function deriveProjectNameFallback(
  projectId: string,
  fileList: string[],
  llmName: string
): string {
  if (isDescriptiveName(llmName, projectId)) return llmName;

  const root = getWorkspaceDir(projectId);
  const pkgRel = fileList.find((f) => f === 'package.json' || f.endsWith('/package.json'));
  if (pkgRel) {
    const full = path.join(root, pkgRel);
    if (fs.existsSync(full)) {
      try {
        const raw = fs.readFileSync(full, 'utf-8');
        const pkg = JSON.parse(raw);
        const n = pkg?.name;
        if (typeof n === 'string' && isDescriptiveName(n, projectId)) return n;
      } catch {
        /* ignore */
      }
    }
  }

  const top = fileList
    .map((f) => f.split('/')[0])
    .filter((d) => d && !d.startsWith('.'));
  if (top.length > 0) {
    const slug = top[0];
    if (isDescriptiveName(slug, projectId))
      return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  return projectId;
}

export async function deriveProjectNameFallbackAsync(
  projectId: string,
  fileList: string[],
  llmName: string
): Promise<string> {
  if (isDescriptiveName(llmName, projectId)) return llmName;
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const pkgRel = fileList.find((f) => f === 'package.json' || f.endsWith('/package.json'));
    if (pkgRel) {
      try {
        const raw = await getFileAsync(projectId, pkgRel);
        const pkg = JSON.parse(raw);
        const n = pkg?.name;
        if (typeof n === 'string' && isDescriptiveName(n, projectId)) return n;
      } catch {
        /* ignore */
      }
    }
    const top = fileList
      .map((f) => f.split('/')[0])
      .filter((d) => d && !d.startsWith('.'));
    if (top.length > 0) {
      const slug = top[0];
      if (isDescriptiveName(slug, projectId))
        return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    }
    return projectId;
  }
  return deriveProjectNameFallback(projectId, fileList, llmName);
}

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

  const combined = fileList.concat(Array.from(fromSearch));
  const readme = combined.filter(isReadme)[0];
  const entrypoints = combined.filter(isEntrypoint);
  const routes = combined.filter(isRoute);
  const data = combined.filter(isDataOrSchema);
  const auth = combined.filter(isAuth);

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

export async function discoverKeyFilePathsAsync(projectId: string): Promise<string[]> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const tree = await repoTreeAsync(projectId);
    const allPaths = flattenTreeToPaths(tree, '', true);
    const filesSummary = await buildFilesSummaryAsync(projectId);
    const fileList = filesSummary.fileList.length > 0 ? filesSummary.fileList : allPaths;
    const searchQueries = ['README', 'main', 'entry', 'index', 'route', 'router', 'api', 'database', 'schema', 'model', 'auth', 'login'];
    const fromSearch = new Set<string>();
    for (const q of searchQueries) {
      const results = await searchRepoAsync(projectId, q);
      for (const r of results) fromSearch.add(r.path);
    }
    const combined = fileList.concat(Array.from(fromSearch));
    const readme = combined.filter(isReadme)[0];
    const entrypoints = combined.filter(isEntrypoint);
    const routes = combined.filter(isRoute);
    const data = combined.filter(isDataOrSchema);
    const auth = combined.filter(isAuth);
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
    const coreCandidates = fileList.filter(
      (p) =>
        !picked.has(p) &&
        (p.includes('/lib/') || p.includes('/libs/') || p.includes('/components/') || p.includes('/app/') || p.includes('/core/'))
    );
    if (picked.size < MAX_KEY_FILES && coreCandidates[0]) picked.add(coreCandidates[0]);
    return Array.from(picked).slice(0, MAX_KEY_FILES);
  }
  return discoverKeyFilePaths(projectId);
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

export async function readKeyFilesAsync(
  projectId: string,
  paths: string[],
  maxCharsPerFile = MAX_CHARS_PER_FILE
): Promise<Array<{ path: string; content: string }>> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const out: Array<{ path: string; content: string }> = [];
    for (const p of paths) {
      try {
        let content = await getFileAsync(projectId, p);
        if (content.length > maxCharsPerFile) {
          content = content.slice(0, maxCharsPerFile) + '\n\n... (truncated)';
        }
        out.push({ path: p, content });
      } catch {
        // skip
      }
    }
    return out;
  }
  return readKeyFiles(projectId, paths, maxCharsPerFile);
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

export async function buildProjectContextAsync(
  projectId: string,
  projectName?: string
): Promise<ProjectContext> {
  const filesSummary = await buildFilesSummaryAsync(projectId);
  const keyPaths = await discoverKeyFilePathsAsync(projectId);
  const keyFiles = await readKeyFilesAsync(projectId, keyPaths);
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
