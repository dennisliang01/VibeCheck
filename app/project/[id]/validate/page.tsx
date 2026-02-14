'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';

export default function ValidatePage() {
  const params = useParams();
  const id = params.id as string;

  return (
    <div className="mx-auto max-w-xl w-full px-6 py-12">
      <Link
        href="/"
        className="text-sm text-[var(--muted)] hover:text-[var(--text)]"
      >
        ← Home
      </Link>
      <div className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 text-center">
        <h1 className="text-lg font-semibold text-[var(--text)]">
          Code validation
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          This is the placeholder for the code-validation flow. Your project ID is <code className="rounded bg-[var(--bg)] px-1">{id}</code>.
        </p>
        <p className="mt-4 text-sm text-[var(--muted)]">
          Teammates can build the validation UI and logic here. Project files are available under <code className="rounded bg-[var(--bg)] px-1">workspaces/{id}/</code> and via the APIs (tree, file, search).
        </p>
        <Link
          href={`/project/${id}`}
          className="mt-6 inline-block text-sm text-[var(--accent)] hover:underline"
        >
          Go to code understanding (Q&A) instead →
        </Link>
      </div>
    </div>
  );
}
