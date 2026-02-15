'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useToast } from '@/components/ToastContext';
import { WorkspaceShell } from '@/components/workspace/WorkspaceShell';

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const id = params.id as string;
  const [status, setStatus] = useState<'loading' | 'building' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function ensureMap() {
      const getRes = await fetch(`/api/project/${id}/map`);
      if (cancelled) return;

      if (getRes.ok) {
        const data = await getRes.json();
        if (data && !data.error) {
          setProjectName(data.name ?? id);
          setStatus('ready');
          // Start codeval in background (fire and forget)
          fetch(`/api/project/${id}/validation/run`, { method: 'POST' }).catch(
            () => {}
          );
          return;
        }
      }

      setStatus('building');
      const postRes = await fetch(`/api/project/${id}/map`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: id }),
      });
      if (cancelled) return;

      if (!postRes.ok) {
        const err = await postRes.json();
        setError(err.error || 'Failed to build map');
        setStatus('error');
        showToast(err.error || 'Failed to build map', 'error');
        return;
      }
      const postData = await postRes.json();
      setProjectName(postData?.name ?? id);
      setStatus('ready');
      // Start codeval in background (fire and forget)
      fetch(`/api/project/${id}/validation/run`, { method: 'POST' }).catch(
        () => {}
      );
    }

    ensureMap();
    return () => { cancelled = true; };
  }, [id, showToast]);

  if (status === 'error') {
    return (
      <div className="px-6 py-12 max-w-xl mx-auto space-y-6">
        <h1 className="sr-only">Project</h1>
        <Link
          href="/"
          className="text-sm text-[var(--muted)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded"
        >
          ← Home
        </Link>
        <div className="rounded-lg border-2 border-[var(--error)] bg-[var(--card)] p-4 text-sm text-[var(--error)]">
          {error}
        </div>
        <Link
          href={`/project/${id}`}
          className="inline-block text-sm text-[var(--accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded"
        >
          Try again →
        </Link>
      </div>
    );
  }

  if (status !== 'ready') {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center gap-6 px-6">
        <h1 className="sr-only">Project</h1>
        <div className="w-full max-w-md">
          <div
            className="progress-bar-indeterminate h-1.5 w-full"
            role="progressbar"
            aria-valuetext={status === 'building' ? 'Building project map' : 'Opening project'}
            aria-label={status === 'building' ? 'Building project map' : 'Opening project'}
          />
        </div>
        <p className="text-lg text-[var(--muted)]">
          {status === 'building' ? 'Building project map…' : 'Opening project…'}
        </p>
        <Link
          href="/"
          className="text-sm text-[var(--muted)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded"
        >
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center gap-6 px-6">
          <div className="w-full max-w-md">
            <div
              className="progress-bar-indeterminate h-1.5 w-full"
              role="progressbar"
              aria-valuetext="Loading workspace"
              aria-label="Loading workspace"
            />
          </div>
          <p className="text-lg text-[var(--muted)]">Loading workspace…</p>
        </div>
      }
    >
      <WorkspaceShell projectId={id} projectName={projectName ?? undefined} />
    </Suspense>
  );
}
