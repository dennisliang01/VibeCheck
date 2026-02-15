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

/**
 * Strip a single common root folder only when the zip has one (e.g. "test_sample/main.py" -> "main.py").
 * Otherwise preserve full structure (e.g. "main.py", "src/file.py" stay as-is).
 */
function stripSingleRootFolder(rawPath: string, allRawPaths: string[]): string {
  const n = normPath(rawPath).replace(/^\/+/, '');
  const parts = n.split('/').filter(Boolean);
  if (parts.length === 0) return n;
  const firstSegments = new Set(
    allRawPaths.map((p) => normPath(p).replace(/^\/+/, '').split('/').filter(Boolean)[0]).filter(Boolean)
  );
  if (firstSegments.size === 1 && parts[0] === firstSegments.values().next().value) {
    if (parts.length === 1) return n;
    return parts.slice(1).join('/');
  }
  return n;
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

  const allRawPaths = extractable.map((e) => normPath(e.entryName));
  let count = 0;
  for (const entry of extractable) {
    const rawPath = normPath(entry.entryName);
    const entryPath = stripSingleRootFolder(rawPath, allRawPaths);
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

/**
 * Yield zip file entries for uploading to blob storage (no fs write).
 * Returns array of { relativePath, data } for non-skipped files under size limit.
 */
export function getZipEntriesForBlob(zip: AdmZip): Array<{ relativePath: string; data: Buffer }> {
  const allEntries = zip.getEntries();
  const extractable = allEntries.filter((e) => {
    if (e.isDirectory) return false;
    if (shouldSkipEntry(normPath(e.entryName))) return false;
    return true;
  });
  if (extractable.length > MAX_FILES) {
    throw new Error(`Too many files in zip (max ${MAX_FILES})`);
  }
  const allRawPaths = extractable.map((e) => normPath(e.entryName));
  const out: Array<{ relativePath: string; data: Buffer }> = [];
  for (const entry of extractable) {
    const rawPath = normPath(entry.entryName);
    const entryPath = stripSingleRootFolder(rawPath, allRawPaths);
    if (!entryPath || entryPath.includes('..')) continue;
    const size = entry.header?.size ?? 0;
    if (size > MAX_SINGLE_FILE_BYTES) continue;
    const data = entry.getData();
    if (!Buffer.isBuffer(data)) continue;
    out.push({ relativePath: entryPath, data });
  }
  return out;
}
