'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useToast } from '@/components/ToastContext';

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const id = params.id as string;
  const [status, setStatus] = useState<'loading' | 'building' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function ensureMapThenGoToLearn() {
      const getRes = await fetch(`/api/project/${id}/map`);
      if (cancelled) return;

      if (getRes.ok) {
        const data = await getRes.json();
        if (data && !data.error) {
          router.replace(`/project/${id}/learn`);
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
      router.replace(`/project/${id}/learn`);
    }

    ensureMapThenGoToLearn();
    return () => { cancelled = true; };
  }, [id, router, showToast]);

  if (status === 'error') {
    return (
      <div className="space-y-6">
        <h1 className="sr-only">Project</h1>
        <Link href="/" className="text-sm text-[var(--muted)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded">
          ← Home
        </Link>
        <div className="rounded-lg border-2 border-[var(--error)] bg-[var(--card)] p-4 text-sm text-[var(--error)]">
          {error}
        </div>
        <Link
          href={`/project/${id}/learn`}
          className="inline-block text-sm text-[var(--accent)] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded"
        >
          Try opening learn anyway →
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <h1 className="sr-only">Project</h1>
      <p className="text-sm text-[var(--muted)]">
        {status === 'building' ? 'Building project map…' : 'Opening project…'}
      </p>
      <Link href="/" className="text-xs text-[var(--muted)] hover:text-[var(--text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded">
        Back to home
      </Link>
    </div>
  );
}
