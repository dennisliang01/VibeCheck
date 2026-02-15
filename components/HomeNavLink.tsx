'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

const PROJECT_PATTERN = /^\/project\/[^/]+/;

export function HomeNavLink() {
  const pathname = usePathname();
  const router = useRouter();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!showModal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowModal(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showModal]);

  if (!pathname || pathname === '/') return null;

  const isProjectPage = PROJECT_PATTERN.test(pathname);

  const handleClick = (e: React.MouseEvent) => {
    if (isProjectPage) {
      e.preventDefault();
      setShowModal(true);
    }
  };

  const handleConfirm = () => {
    setShowModal(false);
    router.push('/');
  };

  const handleCancel = () => setShowModal(false);

  return (
    <>
      <a
        href="/"
        onClick={handleClick}
        className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-1.5 text-sm font-medium text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
      >
        Home
      </a>
      {showModal && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="go-home-dialog-title"
        >
          <div className="mx-4 w-full max-w-sm rounded-lg border border-[var(--border)] bg-[var(--card)] p-6 shadow-xl">
            <h2
              id="go-home-dialog-title"
              className="text-base font-semibold text-[var(--text)]"
            >
              Go home?
            </h2>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Your progress will be lost. Are you sure you want to leave?
            </p>
            <div className="mt-6 flex gap-3 justify-end">
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-lg border border-[var(--border)] bg-transparent px-4 py-2 text-sm font-medium text-[var(--text)] hover:bg-[var(--bg)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
              >
                Go home
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
