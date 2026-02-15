import type { Metadata } from 'next';
import './globals.css';
import { ToastProvider } from '@/components/ToastContext';
import { ThemeProvider } from '@/components/ThemeContext';
import { HomeNavLink } from '@/components/HomeNavLink';
import { ThemeToggle } from '@/components/ThemeToggle';

export const metadata: Metadata = {
  title: 'VibeRight',
  description: 'Learn by answering code-understanding questions on your project',
};

const themeScript = `
(function() {
  var s = localStorage.getItem('viberight-theme');
  var p = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: light)').matches;
  document.documentElement.setAttribute('data-theme', s === 'light' || (!s && p) ? 'light' : 'dark');
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <ThemeProvider>
          <ToastProvider>
            <a
              href="#main-content"
              className="fixed left-4 top-4 z-[100] -translate-y-20 rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white shadow-lg transition-transform focus:translate-y-0 focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2 focus:ring-offset-[var(--bg)]"
            >
              Skip to content
            </a>
            <header className="border-b border-[var(--border)] border-opacity-50 px-6 py-4 flex items-center justify-between gap-4">
              <a
                href="/"
                className="text-base font-medium text-[var(--text)] hover:text-[var(--accent)] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] rounded"
              >
                VibeRight
              </a>
              <div className="flex items-center gap-2">
                <HomeNavLink />
                <ThemeToggle />
              </div>
            </header>
            <main id="main-content" className="min-h-[calc(100vh-4rem)] flex flex-col" tabIndex={-1}>{children}</main>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
