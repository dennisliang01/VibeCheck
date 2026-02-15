import fs from 'fs';
import path from 'path';
import {
  isBlobStorageAvailable,
  blobGetProjectFileContent,
  blobListProjectPaths,
  blobProjectExists,
} from './blobStorage';

/** On Vercel, process.cwd() is read-only; use /tmp for writable workspace and data dirs. */
export function getWorkspacesDirPath(): string {
  return process.env.VERCEL ? path.join('/tmp', 'workspaces') : path.join(process.cwd(), 'workspaces');
}

function getDataDirPath(): string {
  return process.env.VERCEL ? path.join('/tmp', 'data') : path.join(process.cwd(), 'data');
}

const MAX_FILES_FOR_SEARCH = 500;

export function getWorkspaceDir(projectId: string): string {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error(`Project not found: ${projectId}`);
  }
  const dir = path.join(getWorkspacesDirPath(), projectId);
  if (!fs.existsSync(dir)) {
    throw new Error(`Project not found: ${projectId}`);
  }
  return dir;
}

export function getDataDir(): string {
  const dataDir = getDataDirPath();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  return dataDir;
}

export function ensureWorkspacesDir(): string {
  const workspacesDir = getWorkspacesDirPath();
  if (!fs.existsSync(workspacesDir)) {
    fs.mkdirSync(workspacesDir, { recursive: true });
  }
  return workspacesDir;
}

export interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
  isFile: boolean;
}

/**
 * Returns file tree for a project (directories and files).
 */
export function repoTree(projectId: string): TreeNode {
  const root = getWorkspaceDir(projectId);
  const projectMapPath = path.join(root, 'project_map.json');
  const maxFiles = 200;

  function walk(dir: string, relativePath: string, fileCount: { current: number }): TreeNode {
    const name = path.basename(dir);
    const node: TreeNode = {
      name,
      path: relativePath || name,
      isFile: false,
    };
    if (fileCount.current >= maxFiles) return node;

    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const dirs: TreeNode[] = [];
    const files: TreeNode[] = [];

    const skipNames = new Set(['project_map.json', 'validation_report.json', 'validation_status.json', 'validation_debug.json']);
    for (const ent of entries) {
      if (skipNames.has(ent.name)) continue;
      const rel = relativePath ? `${relativePath}/${ent.name}` : ent.name;
      if (ent.isDirectory()) {
        dirs.push(walk(path.join(dir, ent.name), rel, fileCount));
      } else {
        fileCount.current++;
        if (fileCount.current <= maxFiles) {
          files.push({ name: ent.name, path: rel, isFile: true });
        }
      }
    }

    node.children = [...dirs, ...files];
    return node;
  }

  const fileCount = { current: 0 };
  const tree = walk(root, '', fileCount);
  tree.name = path.basename(root);
  tree.path = '';
  return tree;
}

/**
 * Read a single file from the project.
 */
export function getFile(projectId: string, filePath: string): string {
  const root = getWorkspaceDir(projectId);
  const fullPath = path.join(root, filePath);
  const normalized = path.normalize(fullPath);
  if (!normalized.startsWith(path.normalize(root))) {
    throw new Error('Invalid path');
  }
  if (!fs.existsSync(normalized) || !fs.statSync(normalized).isFile()) {
    throw new Error(`File not found: ${filePath}`);
  }
  return fs.readFileSync(normalized, 'utf-8');
}

/**
 * Simple text search over file contents (in-memory, no vector DB).
 */
export function searchRepo(projectId: string, query: string): Array<{ path: string; line: number; snippet: string }> {
  const root = getWorkspaceDir(projectId);
  const results: Array<{ path: string; line: number; snippet: string }> = [];
  const q = query.toLowerCase();
  let filesScanned = 0;

  function scan(dir: string, relativePrefix: string) {
    if (filesScanned >= MAX_FILES_FOR_SEARCH) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const ent of entries) {
      const rel = relativePrefix ? `${relativePrefix}/${ent.name}` : ent.name;
      if (ent.isDirectory()) {
        if (ent.name !== 'node_modules' && ent.name !== '.git') {
          scan(path.join(dir, ent.name), rel);
        }
      } else {
        filesScanned++;
        if (filesScanned > MAX_FILES_FOR_SEARCH) return;
        const fullPath = path.join(dir, ent.name);
        try {
          const content = fs.readFileSync(fullPath, 'utf-8');
          const lines = content.split(/\r?\n/);
          lines.forEach((line, i) => {
            if (line.toLowerCase().includes(q)) {
              results.push({
                path: rel,
                line: i + 1,
                snippet: line.trim().slice(0, 120),
              });
            }
          });
        } catch {
          // skip binary or unreadable
        }
      }
    }
  }

  scan(root, '');
  return results.slice(0, 100);
}

// ---------- Async APIs for Vercel Blob (persistent storage) ----------

function pathsToTree(paths: string[], rootName: string): TreeNode {
  const root: TreeNode = { name: rootName, path: '', isFile: false, children: [] };
  const seen = new Map<string, TreeNode>();
  seen.set('', root);

  const skipBasenames = new Set(['project_map.json', 'validation_report.json', 'validation_status.json', 'validation_debug.json']);
  for (const p of paths) {
    if (!p) continue;
    const base = p.replace(/\\/g, '/').split('/').pop() ?? '';
    if (skipBasenames.has(base)) continue;
    const parts = p.replace(/\\/g, '/').split('/').filter(Boolean);
    let prefix = '';
    for (let i = 0; i < parts.length; i++) {
      const isFile = i === parts.length - 1;
      const seg = parts[i];
      const key = prefix ? `${prefix}/${seg}` : seg;
      if (seen.has(key)) continue;
      const parentKey = prefix;
      const parent = seen.get(parentKey) ?? root;
      const node: TreeNode = {
        name: seg,
        path: key,
        isFile,
        children: isFile ? undefined : [],
      };
      seen.set(key, node);
      if (parent.children) parent.children.push(node);
      prefix = key;
    }
  }
  return root;
}

export async function getFileAsync(projectId: string, filePath: string): Promise<string> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    return blobGetProjectFileContent(projectId, filePath);
  }
  return getFile(projectId, filePath);
}

export async function repoTreeAsync(projectId: string): Promise<TreeNode> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const exists = await blobProjectExists(projectId);
    if (!exists) throw new Error(`Project not found: ${projectId}`);
    const paths = await blobListProjectPaths(projectId);
    return pathsToTree(paths, projectId);
  }
  return repoTree(projectId);
}

const MAX_FILES_SEARCH_BLOB = 100;

export async function searchRepoAsync(
  projectId: string,
  query: string
): Promise<Array<{ path: string; line: number; snippet: string }>> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const paths = await blobListProjectPaths(projectId);
    const q = query.toLowerCase();
    const results: Array<{ path: string; line: number; snippet: string }> = [];
    const toScan = paths.filter((p) => !p.includes('node_modules') && !p.includes('.git')).slice(0, MAX_FILES_SEARCH_BLOB);
    for (const rel of toScan) {
      try {
        const content = await blobGetProjectFileContent(projectId, rel);
        const lines = content.split(/\r?\n/);
        lines.forEach((line, i) => {
          if (line.toLowerCase().includes(q)) {
            results.push({ path: rel, line: i + 1, snippet: line.trim().slice(0, 120) });
          }
        });
      } catch {
        // skip
      }
      if (results.length >= 100) break;
    }
    return results.slice(0, 100);
  }
  return searchRepo(projectId, query);
}
