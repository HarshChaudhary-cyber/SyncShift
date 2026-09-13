'use client';

import React from 'react';
import Link from 'next/link';

export default function LandingFooter() {
  return (
    <footer className="bg-[var(--bg-primary)] border-t border-[var(--border-color)] py-12 px-4 sm:px-6 lg:px-8 text-[var(--text-secondary)] text-xs">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand & Tagline */}
        <div className="flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
          <Link
            href="/"
            className="flex items-center gap-2 text-[var(--text-primary)] font-extrabold text-base tracking-tight hover:opacity-90 transition"
          >
            <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-xs">
              ⚡
            </div>
            <span>SyncShift</span>
          </Link>
          <span className="hidden sm:inline text-[var(--text-muted)]">·</span>
          <p className="text-[var(--text-secondary)]">
            Schedule conflict detector for university students working part-time jobs.
          </p>
        </div>

        {/* Links */}
        <div className="flex flex-wrap items-center justify-center gap-6">
          <Link
            href="/privacy"
            className="hover:text-[var(--text-primary)] transition-colors"
          >
            Privacy
          </Link>
          <Link
            href="/terms"
            className="hover:text-[var(--text-primary)] transition-colors"
          >
            Terms
          </Link>
          <a
            href="https://github.com/HarshChaudhary-cyber/SyncShift"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--text-primary)] transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://github.com/HarshChaudhary-cyber/SyncShift"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--text-primary)] transition-colors"
          >
            Source
          </a>
        </div>
      </div>

      <div className="max-w-6xl mx-auto mt-8 pt-6 border-t border-[var(--border-color)] flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-[var(--text-muted)]">
        <p>© 2026 SyncShift. Free tool for student workers.</p>
        <p>Crafted for students balancing academic excellence and financial independence.</p>
      </div>
    </footer>
  );
}
