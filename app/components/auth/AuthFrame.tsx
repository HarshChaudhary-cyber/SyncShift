'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { MoonIcon, SunIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import { useThemeContext } from '@/context/ThemeContext';
import Brand from '@/components/ui/Brand';
import CampusIllustration from '@/components/landing/CampusIllustration';
import './auth.css';

export default function AuthFrame({ children }: { children: ReactNode }) {
  const { resolvedTheme, toggleTheme } = useThemeContext();
  return <div className="auth-page">
    <header className="auth-header">
      <Brand />
      <div><Link href="/" className="auth-home"><ArrowLeftIcon /> Back to home</Link>
        <button type="button" onClick={toggleTheme} aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}>
          {resolvedTheme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
    <main className="auth-layout">
      <section className="auth-story" aria-labelledby="auth-story-title">
        <p className="auth-eyebrow">ONE CAMPUS. CONNECTED DAYS.</p>
        <h2 id="auth-story-title">Your university day,<br /><span>in sync.</span></h2>
        <p>One workspace for university schedules, teaching, and personal plans.</p>
        <div className="auth-campus" aria-hidden="true"><CampusIllustration role="student" /></div>
        <p className="auth-boundary">Shared academic schedules.<br />Personal space to plan.</p>
      </section>
      <section className="auth-panel" aria-label="Account access">{children}</section>
    </main>
    <footer className="auth-footer">Students · Professors · University administration</footer>
  </div>;
}
