'use client';

import React from 'react';
import { useStudentAcademic } from '../layout';
import Link from 'next/link';

/**
 * Student Timetable page — shows the student's official university timetable
 * (enrolled courses and their scheduled meeting times).
 * Links to the academics sub-pages for enrollment management.
 */
export default function StudentTimetablePage() {
  const { status, profile, loading, institution, membership } = useStudentAcademic();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <svg width={32} height={32} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="animate-spin text-indigo-400" aria-hidden="true">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <p className="text-[var(--text-secondary)] text-sm">Loading timetable…</p>
        </div>
      </div>
    );
  }

  if (!institution) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">My Timetable</h1>
        <div className="p-6 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-start gap-3">
          <span className="text-2xl">📋</span>
          <div className="text-sm space-y-2">
            <p className="font-bold text-amber-300">No University Linked</p>
            <p className="text-amber-200/80">
              Your account is not associated with an institution. Please contact your university administrator or registrar to link your student profile.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">My Timetable</h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Your official university schedule from {institution.name}
          </p>
        </div>
        <Link
          href="/student/courses"
          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition"
        >
          Manage Courses →
        </Link>
      </div>

      {/* Redirect to the existing academic courses page for now */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div className="text-center py-8 space-y-4">
          <span className="text-4xl">🗓️</span>
          <p className="text-sm text-[var(--text-secondary)]">
            Your timetable is managed through your course enrollments.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/student/courses"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition"
            >
              📚 View My Courses
            </Link>
            <Link
              href="/student/calendar"
              className="px-4 py-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition"
            >
              📅 Open Calendar
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
