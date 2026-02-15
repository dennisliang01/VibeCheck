'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ValidateRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  useEffect(() => {
    router.replace(`/project/${id}?tab=validation`);
  }, [id, router]);

  return (
    <div className="flex items-center justify-center py-16">
      <p className="text-sm text-[var(--muted)]">Redirecting…</p>
    </div>
  );
}
