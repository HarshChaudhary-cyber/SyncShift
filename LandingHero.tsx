'use client';

import React from 'react';
import { motion } from 'framer-motion';

export interface LandingHeroProps {
  onCtaClick?: () => void;
  className?: string;
}

export const LandingHero: React.FC<LandingHeroProps> = ({
  onCtaClick,
  className = '',
}) => {
  return (
    <div className={`min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white ${className}`}>
      {/* Minimal Navigation Bar */}
      <header className="w-full max-w-6xl mx-auto px-6 h-20 flex items-center justify-between border-b border-zinc-100 dark:border-zinc-900/80">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-md bg-indigo-600 dark:bg-indigo-500 flex items-center justify-center text-white font-bold text-sm shadow-sm">
            S
          </div>
          <span className="font-semibold tracking-tight text-zinc-900 dark:text-zinc-100 text-sm">
            SyncShift
          </span>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="#features"
            className="text-xs text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors"
          >
            How it works
          </a>
          <button
            onClick={onCtaClick}
            className="text-xs font-medium px-3.5 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 transition-colors"
          >
            Sign in
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center max-w-5xl mx-auto px-6 py-20 sm:py-28 text-center">
        {/* Subtle, single entrance animation */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center max-w-2xl mx-auto"
        >
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/80 text-[11px] font-medium text-zinc-600 dark:text-zinc-400 mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />
            Built for working college students
          </div>

          {/* Primary Headline */}
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50 leading-[1.12]">
            Stop finding schedule conflicts the hard way.
          </h1>

          {/* Problem Statement */}
          <p className="mt-5 text-base sm:text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed max-w-xl font-normal">
            Your university portal exports raw <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">.ics</span> files. Your job sends weekly shift rosters. We catch every overlapping lab, late lecture, and closing shift before your semester begins.
          </p>

          {/* Single Focused CTA */}
          <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
            <button
              onClick={onCtaClick}
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-950 font-medium text-sm transition-all shadow-sm active:scale-[0.99]"
            >
              Check My Schedule
              <svg
                className="ml-2 w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
            <span className="text-xs text-zinc-500 dark:text-zinc-500">
              No registration required • Free forever
            </span>
          </div>
        </motion.div>

        {/* Product Screenshot / App Preview Placeholder */}
        <div className="w-full mt-16 max-w-4xl">
          <div className="relative rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 p-2 shadow-2xl shadow-zinc-200/50 dark:shadow-black/60">
            {/* Window chrome header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-200/80 dark:border-zinc-800/80 mb-2">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
                <div className="w-2.5 h-2.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
              </div>
              <span className="text-[11px] font-mono text-zinc-600 dark:text-zinc-400">
                app.syncshift.dev/calendar
              </span>
              <div className="w-10" />
            </div>

            {/* Realistic SaaS Calendar Mockup */}
            <div className="rounded-lg bg-white dark:bg-zinc-950 border border-zinc-200/60 dark:border-zinc-800/60 p-4 sm:p-6 text-left">
              <div className="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    Fall 2026 Semester Schedule
                  </h3>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    16 Credits enrolled • 18 Shift hours/week
                  </p>
                </div>

                {/* Conflict Alert Pill */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs font-medium animate-pulse">
                  <span className="h-2 w-2 rounded-full bg-rose-600" />
                  1 Conflict Detected
                </div>
              </div>

              {/* Day Grid Preview */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                {/* Tuesday Column */}
                <div className="p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <div className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 mb-2.5">
                    Tuesday
                  </div>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <div className="font-medium text-blue-900 dark:text-blue-200">CS 210: Data Structures</div>
                      <div className="text-[10px] text-blue-700 dark:text-blue-300">09:30 AM – 11:00 AM</div>
                    </div>
                    <div className="p-2 rounded bg-emerald-50 dark:bg-emerald-950/50 border-l-2 border-emerald-600 text-xs">
                      <div className="font-medium text-emerald-900 dark:text-emerald-200">IT Helpdesk Shift</div>
                      <div className="text-[10px] text-emerald-700 dark:text-emerald-300">01:00 PM – 05:00 PM</div>
                    </div>
                  </div>
                </div>

                {/* Wednesday Column (With Conflict) */}
                <div className="p-3 rounded-lg border border-rose-200 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10">
                  <div className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 mb-2.5 flex items-center justify-between">
                    <span>Wednesday</span>
                    <span className="text-[10px] text-rose-600 dark:text-rose-400 font-medium">Overlap</span>
                  </div>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <div className="font-medium text-blue-900 dark:text-blue-200">PHYS 150 Lab</div>
                      <div className="text-[10px] text-blue-700 dark:text-blue-300">02:00 PM – 05:00 PM</div>
                    </div>
                    {/* Conflict item */}
                    <div className="p-2 rounded bg-rose-100/80 dark:bg-rose-950/80 border-2 border-rose-600 text-xs shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-rose-950 dark:text-rose-200">Dining Hall Cashier</span>
                        <span className="text-[9px] uppercase px-1 py-0.5 rounded bg-rose-600 text-white font-semibold">Conflict</span>
                      </div>
                      <div className="text-[10px] text-rose-800 dark:text-rose-300 mt-0.5">
                        04:00 PM – 08:00 PM (1 hr overlap)
                      </div>
                    </div>
                  </div>
                </div>

                {/* Thursday Column */}
                <div className="p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <div className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 mb-2.5">
                    Thursday
                  </div>
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-blue-50 dark:bg-blue-950/50 border-l-2 border-blue-600 text-xs">
                      <div className="font-medium text-blue-900 dark:text-blue-200">MATH 220: Linear Algebra</div>
                      <div className="text-[10px] text-blue-700 dark:text-blue-300">11:00 AM – 12:30 PM</div>
                    </div>
                    <div className="p-2 rounded bg-emerald-50 dark:bg-emerald-950/50 border-l-2 border-emerald-600 text-xs">
                      <div className="font-medium text-emerald-900 dark:text-emerald-200">Library Circulation Desk</div>
                      <div className="text-[10px] text-emerald-700 dark:text-emerald-300">02:00 PM – 06:00 PM</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="w-full max-w-6xl mx-auto px-6 py-8 border-t border-zinc-100 dark:border-zinc-900 text-xs text-zinc-600 dark:text-zinc-400 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>© {new Date().getFullYear()} SyncShift. Free tool for student workers.</div>
        <div className="flex gap-4">
          <a href="#privacy" className="hover:underline">Privacy</a>
          <a href="#terms" className="hover:underline">Terms</a>
          <a href="https://github.com" className="hover:underline">Source</a>
        </div>
      </footer>
    </div>
  );
};

export default LandingHero;
