import fs from 'fs';
import path from 'path';

const WORKSPACES_DIR = path.join(process.cwd(), 'workspaces');
const DATA_DIR = path.join(process.cwd(), 'data');

const MAX_FILES_FOR_SEARCH = 500;

export function getWorkspaceDir(projectId: string): string {
  const dir = path.join(WORKSPACES_DIR, projectId);
  if (!fs.existsSync(dir)) {
    throw new Error(`Project not found: ${projectId}`);
  }
  return dir;
}

export function getDataDir(): string {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  return DATA_DIR;
}

export function ensureWorkspacesDir(): string {
  if (!fs.existsSync(WORKSPACES_DIR)) {
    fs.mkdirSync(WORKSPACES_DIR, { recursive: true });
  }
  return WORKSPACES_DIR;
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

    for (const ent of entries) {
      if (ent.name === 'project_map.json') continue;
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
