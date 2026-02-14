import fs from 'fs';
import path from 'path';
import type { FilesSummary } from './llm/types';
import { getWorkspaceDir } from './workspace';

export function buildFilesSummary(projectId: string): FilesSummary {
  const root = getWorkspaceDir(projectId);
  const fileList: string[] = [];
  const extensions: Record<string, number> = {};
  let totalSizeBytes = 0;
  const maxFiles = 300;

  function walk(dir: string, relativePrefix: string) {
    if (fileList.length >= maxFiles) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const ent of entries) {
      if (ent.name === 'project_map.json') continue;
      const rel = relativePrefix ? `${relativePrefix}/${ent.name}` : ent.name;
      if (ent.isDirectory()) {
        if (ent.name !== 'node_modules' && ent.name !== '.git') {
          walk(path.join(dir, ent.name), rel);
        }
      } else {
        fileList.push(rel);
        const ext = path.extname(ent.name) || '.none';
        extensions[ext] = (extensions[ext] ?? 0) + 1;
        try {
          totalSizeBytes += fs.statSync(path.join(dir, ent.name)).size;
        } catch {
          // ignore
        }
      }
    }
  }

  walk(root, '');
  return {
    fileCount: fileList.length,
    fileList,
    totalSizeBytes,
    extensions,
  };
}
