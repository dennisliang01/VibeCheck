'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/ToastContext';

export default function HomePage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const uploadErrorRef = useRef<HTMLParagraphElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doUpload = async (fileToUpload: File) => {
    setError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', fileToUpload);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Upload failed');
      setFile(null);
      showToast('Project uploaded successfully', 'success');
      router.push(`/project/${data.projectId}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a .zip file');
      showToast('Please select a .zip file', 'error');
      requestAnimationFrame(() => uploadErrorRef.current?.focus() ?? fileInputRef.current?.focus());
      return;
    }
    await doUpload(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    if (selected) {
      doUpload(selected);
    }
    e.target.value = '';
  };

  const handleLoadSample = async () => {
    setError(null);
    setLoadingSample(true);
    try {
      const res = await fetch('/api/load-sample', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load sample');
      showToast('Sample project loaded', 'success');
      router.push(`/project/${data.projectId}?sample=1`);
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
      <section className="flex flex-col justify-center py-16 min-h-[calc(100vh-4rem)]">
        <div className="text-center">
          <h1 className="hero-title-start text-4xl font-semibold text-[var(--text)] tracking-tight">
            VibeRight
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
              onChange={handleFileChange}
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
              {uploading ? 'Uploading…' : file ? file.name : 'Upload code'}
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
    </div>
  );
}
