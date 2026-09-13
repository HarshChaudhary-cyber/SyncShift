import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import NotificationRegistrar from '@/components/NotificationRegistrar';
import SyncShiftAssistant from '@/components/assistant/SyncShiftAssistant';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: 'SyncShift – Student Schedule Conflict Detector',
  description:
    'Detect time conflicts between your university class schedule and work shifts before your semester begins.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('syncshift-theme') || 'dark';
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  var resolvedTheme = saved === 'system' 
                    ? (prefersDark ? 'dark' : 'light') 
                    : saved;
                  document.documentElement.setAttribute('data-theme', resolvedTheme);
                  if (resolvedTheme === 'dark') {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch(e) {
                  document.documentElement.setAttribute('data-theme', 'dark');
                  document.documentElement.classList.add('dark');
                }
              })()
            `,
          }}
        />
      </head>
      <body className="font-sans antialiased min-h-screen overflow-x-hidden">
        <AuthProvider>
          <ThemeProvider>
            <NotificationRegistrar />
            {children}
            <SyncShiftAssistant />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
