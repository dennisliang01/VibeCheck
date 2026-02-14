'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useToast } from '@/components/ToastContext';

export default function HomePage() {
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const nextStepSectionRef = useRef<HTMLDivElement>(null);
  const uploadErrorRef = useRef<HTMLParagraphElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [nextStepInView, setNextStepInView] = useState(false);

  // When user uploads, scroll down to reveal the next step (Apple-style)
  useEffect(() => {
    if (!projectId) return;
    const t = setTimeout(() => {
      const reduceMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      nextStepSectionRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    }, 150);
    return () => clearTimeout(t);
  }, [projectId]);

  // Reveal animation when next step section enters viewport
  useEffect(() => {
    if (!projectId) return;
    const el = nextStepSectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) setNextStepInView(true);
      },
      { threshold: 0.15, rootMargin: '0px 0px -10% 0px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [projectId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a .zip file');
      showToast('Please select a .zip file', 'error');
      requestAnimationFrame(() => uploadErrorRef.current?.focus() ?? fileInputRef.current?.focus());
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Upload failed');
      setProjectId(data.projectId);
      setFile(null);
      showToast('Project uploaded successfully', 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleLoadSample = async () => {
    setError(null);
    setLoadingSample(true);
    try {
      const res = await fetch('/api/load-sample', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load sample');
      setProjectId(data.projectId);
      showToast('Sample project loaded', 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load sample';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoadingSample(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl w-full px-6 flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Hero: full screen until upload; then collapses so arrow extends from form */}
      <section
        className={`flex flex-col justify-center py-16 transition-[min-height] duration-500 ${
          projectId ? 'min-h-0 pb-0' : 'min-h-[calc(100vh-4rem)]'
        }`}
      >
        <div className="text-center">
          <h1 className="hero-title-start text-4xl font-semibold text-[var(--text)] tracking-tight">
            VibeCheck
          </h1>
          <p className="hero-subtitle-start mt-2 text-[var(--muted)]">
            Know your system. Ship with confidence.
          </p>
        </div>

        <div className="hero-block-start relative flex flex-col items-center mt-10">
          <form id="upload-form" onSubmit={handleUpload} className="flex w-full flex-col gap-4">
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border border-dashed border-[var(--border)] bg-[var(--card)] py-8 px-6 transition-colors hover:border-[var(--muted)]">
            <input
              ref={fileInputRef}
              id="upload-file"
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-[var(--accent)]"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="text-sm font-medium text-[var(--muted)]">
              {file ? file.name : 'Upload code'}
            </span>
            <span className="text-xs text-[var(--muted)] opacity-80">.zip · Max 50MB</span>
          </label>

          {error && (
            <p id="upload-error" ref={uploadErrorRef} className="text-center text-sm text-[var(--error)]" tabIndex={-1} role="alert">
              {error}
            </p>
          )}

          <div className="flex gap-3 justify-center">
            <button
              type="submit"
              disabled={uploading || !file}
              aria-describedby={error ? 'upload-error' : undefined}
              className="rounded-lg bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-40 disabled:pointer-events-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </button>
            <button
              type="button"
              onClick={handleLoadSample}
              disabled={loadingSample}
              className="rounded-lg border border-[var(--border)] px-5 py-2.5 text-sm font-medium text-[var(--muted)] hover:bg-[var(--card)] hover:text-[var(--text)] disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
            >
              {loadingSample ? 'Loading…' : 'Sample'}
            </button>
          </div>
        </form>
        </div>
      </section>

      {/* Arrow extends from upload box down to choice cards */}
      {projectId && (
        <section
          ref={nextStepSectionRef}
          className="scroll-mt-0 pt-0 min-h-[calc(100vh-4rem)] flex flex-col justify-start"
          aria-label="Next step"
        >
          <div
            className={`flex flex-col items-center w-full transition-all duration-500 ease-out ${
              nextStepInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            }`}
          >
            {/* One continuous arrow: long vertical from form, then Y into cards */}
            <div className="w-full px-2 flex flex-col items-stretch">
              <svg
                width="100%"
                height="180"
                viewBox="0 0 600 180"
                preserveAspectRatio="none"
                className="overflow-visible shrink-0"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <marker
                    id="arrowhead-left"
                    markerWidth="6"
                    markerHeight="6"
                    refX="4"
                    refY="3"
                    orient="auto"
                  >
                    <path d="M0 0 L6 3 L0 6 Z" fill="var(--accent)" />
                  </marker>
                  <marker
                    id="arrowhead-right"
                    markerWidth="6"
                    markerHeight="6"
                    refX="4"
                    refY="3"
                    orient="auto"
                  >
                    <path d="M0 0 L6 3 L0 6 Z" fill="var(--accent)" />
                  </marker>
                </defs>
                {/* Vertical stem: from upload box (top) all the way down to split */}
                <line
                  x1="300"
                  y1="0"
                  x2="300"
                  y2="140"
                  stroke="var(--accent)"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  strokeLinecap="round"
                  style={{ animation: 'flowDown 0.6s linear infinite' }}
                />
                {/* Left branch: split → left → down to Code understanding card */}
                <path
                  d="M300 140 H100 V180"
                  stroke="var(--accent)"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                  markerEnd="url(#arrowhead-left)"
                  style={{ animation: 'flowDown 0.6s linear infinite' }}
                />
                {/* Right branch: split → right → down to Code validation card */}
                <path
                  d="M300 140 H500 V180"
                  stroke="var(--accent)"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                  markerEnd="url(#arrowhead-right)"
                  style={{ animation: 'flowDown 0.6s linear infinite' }}
                />
              </svg>

              <div className="w-full grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 items-stretch mt-3">
                <Link
                  href={`/project/${projectId}`}
                  className="rounded-xl bg-[var(--accent)] p-5 sm:p-6 text-center hover:bg-[var(--accent-hover)] transition-colors block border border-transparent hover:border-[var(--accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
                >
                  <h2 className="text-base font-semibold text-white">Code understanding</h2>
                  <p className="mt-1.5 text-sm text-white/90">
                    Assess whether you truly understand how the code works.
                  </p>
                </Link>

                <p className="text-sm text-[var(--muted)] flex items-center justify-center py-4 sm:py-8 order-first sm:order-none">
                  Choose one
                </p>

                <Link
                  href={`/project/${projectId}/validate`}
                  className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 sm:p-6 text-center hover:border-[var(--muted)] hover:bg-[var(--border)]/30 transition-colors block focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]"
                >
                  <h2 className="text-base font-semibold text-[var(--text)]">Code validation</h2>
                  <p className="mt-1.5 text-sm text-[var(--muted)]">
                  Evaluate your code like a senior engineer would
                  </p>
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
