import type { Metadata } from 'next';
import './globals.css';
import { ToastProvider } from '@/components/ToastContext';
import { ThemeProvider } from '@/components/ThemeContext';
import { HomeNavLink } from '@/components/HomeNavLink';
import { ThemeToggle } from '@/components/ThemeToggle';

export const metadata: Metadata = {
  title: 'VibeCheck',
  description: 'Learn by answering code-understanding questions on your project',
};

const themeScript = `
(function() {
  var s = localStorage.getItem('vibecheck-theme');
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
            <header className="border-b border-[var(--border)] border-opacity-50 px-6 py-4 flex items-center justify-between gap-4">
              <a href="/" className="text-base font-medium text-[var(--text)] hover:text-[var(--accent)] transition-colors">
                VibeCheck
              </a>
              <div className="flex items-center gap-2">
                <HomeNavLink />
                <ThemeToggle />
              </div>
            </header>
            <main className="min-h-[calc(100vh-4rem)] flex flex-col">{children}</main>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
