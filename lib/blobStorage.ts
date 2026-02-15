/**
 * Vercel Blob storage for workspaces and data when running on Vercel.
 * Uses BLOB_READ_WRITE_TOKEN (set automatically when a Blob store is connected to the project).
 */

import { put, list, del } from '@vercel/blob';

const WORKSPACES_PREFIX = 'workspaces/';
const DATA_PREFIX = 'data/';

function workspacePath(projectId: string, relativePath: string): string {
  const normalized = relativePath.replace(/\\/g, '/').replace(/^\/+/, '');
  return `${WORKSPACES_PREFIX}${projectId}/${normalized}`;
}

export async function blobPutProjectFile(
  projectId: string,
  relativePath: string,
  content: string | Buffer
): Promise<void> {
  const pathname = workspacePath(projectId, relativePath);
  await put(pathname, content, {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
  });
}

export async function blobGetProjectFileContent(
  projectId: string,
  relativePath: string
): Promise<string> {
  const pathname = workspacePath(projectId, relativePath);
  const { blobs } = await list({ prefix: pathname, limit: 1 });
  const blob = blobs.find((b) => b.pathname === pathname);
  if (!blob?.url) throw new Error(`File not found: ${relativePath}`);
  const res = await fetch(blob.url);
  if (!res.ok) throw new Error(`File not found: ${relativePath}`);
  return res.text();
}

export async function blobListProjectPaths(projectId: string): Promise<string[]> {
  const prefix = `${WORKSPACES_PREFIX}${projectId}/`;
  const paths: string[] = [];
  let cursor: string | undefined;
  do {
    const result = await list({ prefix, limit: 1000, cursor });
    for (const b of result.blobs) {
      const rel = b.pathname.slice(prefix.length);
      if (rel && !rel.includes('..')) paths.push(rel);
    }
    cursor = result.cursor ?? undefined;
  } while (cursor);
  return paths;
}

export async function blobProjectExists(projectId: string): Promise<boolean> {
  const prefix = `${WORKSPACES_PREFIX}${projectId}/`;
  const { blobs } = await list({ prefix, limit: 1 });
  return blobs.length > 0;
}

export async function blobListProjectIds(): Promise<string[]> {
  const { blobs } = await list({ prefix: WORKSPACES_PREFIX, limit: 1000 });
  const ids = new Set<string>();
  for (const b of blobs) {
    const after = b.pathname.slice(WORKSPACES_PREFIX.length);
    const idx = after.indexOf('/');
    if (idx > 0) ids.add(after.slice(0, idx));
  }
  return Array.from(ids);
}

export async function blobPutDataFile(pathname: string, content: string): Promise<void> {
  const full = pathname.startsWith(DATA_PREFIX) ? pathname : `${DATA_PREFIX}${pathname}`;
  await put(full, content, {
    access: 'public',
    addRandomSuffix: false,
    allowOverwrite: true,
  });
}

export async function blobGetDataFile(pathname: string): Promise<string | null> {
  const full = pathname.startsWith(DATA_PREFIX) ? pathname : `${DATA_PREFIX}${pathname}`;
  const { blobs } = await list({ prefix: full, limit: 1 });
  const blob = blobs.find((b) => b.pathname === full);
  if (!blob?.url) return null;
  const res = await fetch(blob.url);
  if (!res.ok) return null;
  return res.text();
}

/** Delete all blobs under a project prefix (e.g. when removing a project). */
export async function blobDeleteProject(projectId: string): Promise<void> {
  const prefix = `${WORKSPACES_PREFIX}${projectId}/`;
  let cursor: string | undefined;
  do {
    const result = await list({ prefix, limit: 500, cursor });
    if (result.blobs.length > 0) {
      await del(result.blobs.map((b) => b.url));
    }
    cursor = result.cursor ?? undefined;
  } while (cursor);
}

export function isBlobStorageAvailable(): boolean {
  return typeof process !== 'undefined' && !!process.env.BLOB_READ_WRITE_TOKEN;
}
