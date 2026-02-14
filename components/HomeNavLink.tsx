'use client';

import { usePathname } from 'next/navigation';

export function HomeNavLink() {
  const pathname = usePathname();
  if (pathname === '/') return null;
  return (
    <a
      href="/"
      className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-1.5 text-sm font-medium text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] transition-colors"
    >
      Home
    </a>
  );
}
