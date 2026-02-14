import AdmZip from 'adm-zip';
import path from 'path';
import fs from 'fs';

export const MAX_FILES = 200;
export const MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024; // 2MB per file

function normPath(p: string): string {
  return p.replace(/\\/g, '/').replace(/\/+/g, '/');
}

function shouldSkipEntry(entryPath: string): boolean {
  const n = normPath(entryPath);
  if (n.includes('__MACOSX') || n.includes('.DS_Store')) return true;
  const segments = n.split('/').filter(Boolean);
  if (segments.some((s) => s.startsWith('.') && s !== '..')) return true;
  return false;
}

function stripRootFolder(entryPath: string): string {
  const n = normPath(entryPath).replace(/^\/+/, '');
  const idx = n.indexOf('/');
  if (idx === -1) return n;
  return n.slice(idx + 1);
}

/**
 * Extract zip into projectDir, skipping __MACOSX, .DS_Store, and files over MAX_SINGLE_FILE_BYTES.
 * Returns the number of files extracted.
 */
export function extractZipToProjectDir(
  zip: AdmZip,
  projectDir: string
): number {
  const allEntries = zip.getEntries();
  const extractable = allEntries.filter((e) => {
    if (e.isDirectory) return false;
    if (shouldSkipEntry(normPath(e.entryName))) return false;
    return true;
  });

  if (extractable.length > MAX_FILES) {
    throw new Error(`Too many files in zip (max ${MAX_FILES})`);
  }

  let count = 0;
  for (const entry of extractable) {
    const rawPath = normPath(entry.entryName);
    const entryPath = stripRootFolder(rawPath);
    if (!entryPath || entryPath.includes('..')) continue;
    const size = entry.header?.size ?? 0;
    if (size > MAX_SINGLE_FILE_BYTES) continue;
    const fullPath = path.join(projectDir, entryPath);
    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    zip.extractEntryTo(entry, dir, false, true);
    count++;
  }
  return count;
}

export function generateProjectId(): string {
  return `proj_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}
