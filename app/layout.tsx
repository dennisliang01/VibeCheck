import type { Metadata } from 'next';
import './globals.css';
import { ToastProvider } from '@/components/ToastContext';

export const metadata: Metadata = {
  title: 'VibeCheck',
  description: 'Learn by answering code-understanding questions on your project',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] antialiased">
        <ToastProvider>
          <header className="border-b border-[var(--border)] border-opacity-50 px-6 py-4">
            <a href="/" className="text-base font-medium text-[var(--text)] hover:text-[var(--accent)] transition-colors">
              VibeCheck
            </a>
          </header>
          <main className="min-h-[calc(100vh-4rem)] flex flex-col">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}
