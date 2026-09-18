'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LandingHeroProps {
  onCtaClick?: () => void;
  onHowItWorksClick?: () => void;
  onImportClick?: () => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const LandingHero: React.FC<LandingHeroProps> = ({
  onCtaClick,
  onHowItWorksClick,
  onImportClick,
  className = '',
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  return (
    <div
      className={`min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col justify-between ${className}`}
    >
      {/* ── Navigation ──────────────────────────────────────────────────── */}
      <header className="relative w-full max-w-6xl mx-auto px-4 sm:px-6 h-16 sm:h-20 flex items-center justify-between border-b border-zinc-100 dark:border-zinc-900 z-30">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-md bg-indigo-600 dark:bg-indigo-500 flex items-center justify-center text-white font-bold text-sm shadow-sm">
            S
          </div>
          <span className="font-semibold tracking-tight text-sm">
            SyncShift
          </span>
        </div>

        {/* Desktop navigation */}
        <nav className="hidden md:flex items-center gap-3">
          <button
            type="button"
            onClick={onHowItWorksClick}
            className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors cursor-pointer"
          >
            How it works
          </button>
          <button
            type="button"
            onClick={onImportClick}
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 hover:border-indigo-300 dark:hover:border-indigo-700 bg-zinc-50 dark:bg-zinc-900 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/40 text-zinc-700 dark:text-zinc-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import .ics
          </button>
          <Link
            href="/login"
            className="text-xs text-zinc-400 hover:text-white transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="text-xs font-medium px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-sm shadow-indigo-950/40"
          >
            Sign up
          </Link>
          <Link
            href="/student/calendar"
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-neutral-700 hover:border-neutral-600 bg-neutral-800 text-neutral-200 transition-colors"
          >
            Calendar App →
          </Link>
        </nav>

        {/* Mobile hamburger button */}
        <div className="flex md:hidden items-center gap-2">
          <Link
            href="/student/calendar"
            className="text-xs font-medium px-2.5 py-1.5 rounded-md bg-indigo-600 text-white"
          >
            App →
          </Link>
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800/60 transition cursor-pointer"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile dropdown drawer */}
        {mobileMenuOpen && (
          <div className="absolute top-full left-0 right-0 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 shadow-xl p-4 flex flex-col gap-2.5 md:hidden z-40">
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                onHowItWorksClick?.();
              }}
              className="text-left py-2 px-3 rounded-lg text-sm text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            >
              How it works
            </button>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                onImportClick?.();
              }}
              className="text-left py-2 px-3 rounded-lg text-sm text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition flex items-center gap-2"
            >
              <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Import timetable (.ics)
            </button>
            <div className="h-px bg-zinc-200 dark:bg-zinc-800 my-1" />
            <Link
              href="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="py-2 px-3 rounded-lg text-sm text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              onClick={() => setMobileMenuOpen(false)}
              className="py-2.5 px-3 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white text-center transition"
            >
              Sign up
            </Link>
          </div>
        )}
      </header>


      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <main className="flex-1 w-full flex flex-col items-center justify-center max-w-5xl mx-auto px-6 py-20 sm:py-28 text-center">
        {/*
          FIX: Single Framer Motion entrance animation on the text group only.
          The screenshot card is rendered outside the motion.div so it doesn't
          need its own animation and doesn't risk an SSR hydration mismatch.
        */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center max-w-2xl mx-auto"
        >
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-[11px] font-medium text-zinc-500 dark:text-zinc-400 mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />
            Built for working college students
          </div>

          {/* Primary headline */}
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 leading-[1.12]">
            Stop finding schedule conflicts the hard way.
          </h1>

          {/* Problem statement */}
          <p className="mt-5 text-base sm:text-lg text-zinc-500 dark:text-zinc-400 leading-relaxed max-w-xl">
            Your university portal exports raw{' '}
            <code className="font-mono text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
              .ics
            </code>{' '}
            files. Your job sends weekly shift rosters. We catch every
            overlapping lab, late lecture, and closing shift before your
            semester begins.
          </p>

          {/* CTA */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={onCtaClick}
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-950 font-medium text-sm transition-all shadow-sm active:scale-[0.99]"
            >
              Check My Schedule
              <svg
                className="ml-2 w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 5l7 7m0 0l-7 7m7-7H3"
                />
              </svg>
            </button>
            <button
              type="button"
              onClick={onImportClick}
              className="w-full sm:w-auto inline-flex items-center justify-center px-5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium text-sm transition-all shadow-sm active:scale-[0.99] gap-2"
            >
              <svg
                className="w-4 h-4 text-indigo-600 dark:text-indigo-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                />
              </svg>
              Import Timetable (.ics)
            </button>
          </div>
          <span className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
            No registration required · Free forever
          </span>
        </motion.div>

        {/* ── App Preview / Screenshot Placeholder ──────────────────────── */}
        <div className="w-full mt-16 max-w-4xl mx-auto">
          <div className="relative rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-2 shadow-2xl shadow-zinc-200/60 dark:shadow-black/60">
            {/* Browser chrome */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-200 dark:border-zinc-800 mb-2">
              <div className="flex items-center gap-1.5">
                {['bg-zinc-300 dark:bg-zinc-700', 'bg-zinc-300 dark:bg-zinc-700', 'bg-zinc-300 dark:bg-zinc-700'].map(
                  (cls, i) => (
                    <div key={i} className={`w-2.5 h-2.5 rounded-full ${cls}`} />
                  ),
                )}
              </div>
              <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
                app.syncshift.dev/student/calendar
              </span>
              <div className="w-12" aria-hidden="true" />
            </div>

            {/* Mini calendar mockup */}
            <div className="rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60 p-4 sm:p-6 text-left">
              <div className="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800">
                <div>
                  <h2 className="text-sm font-semibold">
                    Fall 2026 Semester Schedule
                  </h2>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    16 Credits enrolled · 18 Shift hours/week
                  </p>
                </div>
                {/* Conflict pill */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs font-medium animate-pulse">
                  <span className="h-2 w-2 rounded-full bg-rose-600" />
                  1 Conflict Detected
                </div>
              </div>

              {/* Three-day preview */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                {/* Tuesday */}
                <div className="p-3 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <p className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 mb-2.5">
                    Tuesday
                  </p>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <p className="font-medium text-blue-900 dark:text-blue-200">
                        CS 210: Data Structures
                      </p>
                      <p className="text-[10px] text-blue-700 dark:text-blue-300">
                        9:30 AM – 11:00 AM
                      </p>
                    </div>
                    <div className="p-2 rounded bg-emerald-50 dark:bg-emerald-950/50 border-l-2 border-emerald-600 text-xs">
                      <p className="font-medium text-emerald-900 dark:text-emerald-200">
                        IT Helpdesk Shift
                      </p>
                      <p className="text-[10px] text-emerald-700 dark:text-emerald-300">
                        1:00 PM – 5:00 PM
                      </p>
                    </div>
                  </div>
                </div>

                {/* Wednesday (conflict) */}
                <div className="p-3 rounded-lg border border-rose-200 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10">
                  <div className="flex items-center justify-between mb-2.5">
                    <p className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      Wednesday
                    </p>
                    <span className="text-[10px] text-rose-600 dark:text-rose-400 font-medium">
                      Overlap
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <p className="font-medium text-blue-900 dark:text-blue-200">
                        PHYS 150 Lab
                      </p>
                      <p className="text-[10px] text-blue-700 dark:text-blue-300">
                        2:00 PM – 5:00 PM
                      </p>
                    </div>
                    <div className="p-2 rounded bg-rose-100/80 dark:bg-rose-950/80 border-2 border-rose-600 text-xs shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-rose-950 dark:text-rose-200">
                          Dining Hall Cashier
                        </span>
                        <span className="text-[9px] uppercase px-1 py-0.5 rounded bg-rose-600 text-white font-semibold">
                          Conflict
                        </span>
                      </div>
                      <p className="text-[10px] text-rose-800 dark:text-rose-300 mt-0.5">
                        4:00 PM – 8:00 PM (1 hr overlap)
                      </p>
                    </div>
                  </div>
                </div>

                {/* Thursday */}
                <div className="p-3 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <p className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 mb-2.5">
                    Thursday
                  </p>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <p className="font-medium text-blue-900 dark:text-blue-200">
                        MATH 220: Linear Algebra
                      </p>
                      <p className="text-[10px] text-blue-700 dark:text-blue-300">
                        11:00 AM – 12:30 PM
                      </p>
                    </div>
                    <div className="p-2 rounded bg-emerald-50 dark:bg-emerald-950/50 border-l-2 border-emerald-600 text-xs">
                      <p className="font-medium text-emerald-900 dark:text-emerald-200">
                        Library Circulation Desk
                      </p>
                      <p className="text-[10px] text-emerald-700 dark:text-emerald-300">
                        2:00 PM – 6:00 PM
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="w-full max-w-6xl mx-auto px-6 py-8 border-t border-zinc-100 dark:border-zinc-900 text-xs text-zinc-400 dark:text-zinc-500 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div suppressHydrationWarning>© {new Date().getFullYear()} SyncShift. Free tool for student workers.</div>
        <div className="flex gap-4">
          <a href="#privacy" className="hover:underline hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
            Privacy
          </a>
          <a href="#terms" className="hover:underline hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors">
            Terms
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          >
            Source
          </a>
        </div>
      </footer>
    </div>
  );
};

export default LandingHero;
