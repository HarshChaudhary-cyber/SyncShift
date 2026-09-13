'use client';

import React from 'react';
import Link from 'next/link';
import { StudentAcademicSummary } from '@/lib/api';

interface AcademicSummaryCardProps {
  academics?: StudentAcademicSummary | null;
  loading?: boolean;
}

export default function AcademicSummaryCard({ academics, loading }: AcademicSummaryCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 animate-pulse">
        <div className="h-5 w-48 bg-slate-700/40 rounded mb-4" />
        <div className="h-4 w-72 bg-slate-700/30 rounded mb-6" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="h-16 bg-slate-700/20 rounded-xl" />
          <div className="h-16 bg-slate-700/20 rounded-xl" />
          <div className="h-16 bg-slate-700/20 rounded-xl" />
          <div className="h-16 bg-slate-700/20 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!academics) {
    return null;
  }

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm hover:border-indigo-500/30 transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[var(--border-color)]">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🎓</span>
            <h3 className="text-base font-bold text-[var(--text-primary)]">
              {academics.institution_name}
            </h3>
            {academics.current_term && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {academics.current_term}
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            {academics.program ? `${academics.program} • ` : ''}
            {academics.year_of_study ? `Year ${academics.year_of_study}` : ''}
            {academics.student_number ? ` • ID: ${academics.student_number}` : ''}
            {academics.department_name ? ` • ${academics.department_name}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Link
            href="/student/academics"
            className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm hover:shadow transition flex items-center gap-1.5"
          >
            <span>Academic Portal</span>
            <span>→</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)]/60 rounded-xl p-3">
          <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-0.5">
            Enrolled Courses
          </span>
          <span className="text-xl font-bold text-indigo-400">
            {academics.enrolled_courses_count}
          </span>
        </div>

        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)]/60 rounded-xl p-3">
          <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-0.5">
            Total Credits
          </span>
          <span className="text-xl font-bold text-emerald-400">
            {academics.enrolled_credits}
          </span>
        </div>

        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)]/60 rounded-xl p-3">
          <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-0.5">
            Active Sections
          </span>
          <span className="text-xl font-bold text-sky-400">
            {academics.enrolled_sections.length}
          </span>
        </div>

        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)]/60 rounded-xl p-3 flex flex-col justify-center">
          <span className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wider block mb-0.5">
            Preferences
          </span>
          <Link
            href="/student/constraints"
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline flex items-center gap-1"
          >
            Manage Rules →
          </Link>
        </div>
      </div>

      {/* Enrolled Sections Preview */}
      {academics.enrolled_sections.length > 0 ? (
        <div className="space-y-2 mt-2">
          <div className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Enrolled Course Sections
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {academics.enrolled_sections.map((sec) => (
              <div
                key={sec.section_id}
                className="p-2.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]/70 flex items-center justify-between text-xs"
              >
                <div className="min-w-0 pr-2">
                  <div className="font-bold text-[var(--text-primary)] truncate flex items-center gap-1.5">
                    <span>{sec.course_code}</span>
                    <span className="px-1.5 py-0.2 bg-indigo-500/20 text-indigo-300 text-[10px] rounded font-mono">
                      Sec {sec.section_code}
                    </span>
                  </div>
                  <div className="text-[11px] text-[var(--text-secondary)] truncate">
                    {sec.course_name}
                  </div>
                  {sec.instructors && sec.instructors.length > 0 && (
                    <div className="text-[10px] text-slate-400 truncate mt-0.5">
                      Prof. {sec.instructors.join(', ')}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-semibold border border-emerald-500/20">
                    {sec.credits} cr
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="py-3 px-4 bg-slate-800/30 rounded-xl border border-dashed border-slate-700 text-center text-xs text-[var(--text-secondary)]">
          No sections enrolled for this term.{' '}
          <Link href="/student/academics" className="text-indigo-400 hover:underline font-semibold">
            Browse course catalog
          </Link>{' '}
          to enroll.
        </div>
      )}
    </div>
  );
}
