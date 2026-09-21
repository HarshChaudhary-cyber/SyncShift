'use client';

import React from 'react';
import Link from 'next/link';
import { ScheduleContextSummary } from '@/lib/api';

interface WeeklyPlanHeroProps {
  onPlanClick: () => void;
  isLoading: boolean;
  contextSummary?: ScheduleContextSummary | null;
  onRevertClick?: () => void;
  hasAppliedPlan?: boolean;
}

export default function WeeklyPlanHero({
  onPlanClick,
  isLoading,
  contextSummary,
  onRevertClick,
  hasAppliedPlan = false,
}: WeeklyPlanHeroProps) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-purple-500/20 bg-gradient-to-br from-[var(--bg-card)] via-[var(--bg-secondary)] to-purple-950/20 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
      {/* Background ambient decorative glow */}
      <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-purple-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-72 h-72 rounded-full bg-pink-500/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-50 dark:bg-purple-500/10 border border-purple-200 dark:border-purple-500/20 text-purple-700 dark:text-purple-300 text-xs font-semibold">
            <span>✨</span>
            <span>Smart Weekly Planning</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
            Plan your week around your university timetable
          </h1>

          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
            SyncShift treats your official university classes as authoritative fixed anchors and automatically
            discovers optimal, conflict-free study and focus windows around your work shifts and life commitments.
          </p>

          {/* Quick Context Summary Metrics */}
          {contextSummary && (
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">🏛️ {contextSummary.enrolled_classes_count}</span>
                <span className="text-[var(--text-secondary)]">Class Meetings</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-amber-700 dark:text-amber-400 font-bold">💼 {contextSummary.fixed_work_shifts_count}</span>
                <span className="text-[var(--text-secondary)]">Work Shifts</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-purple-600 dark:text-purple-400 font-bold">🎯 {contextSummary.pending_tasks_count}</span>
                <span className="text-[var(--text-secondary)]">Goals ({contextSummary.total_study_hours_needed}h needed)</span>
              </div>
            </div>
          )}
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-col sm:flex-row lg:flex-col items-stretch gap-3 shrink-0">
          <button
            onClick={onPlanClick}
            disabled={isLoading}
            className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 via-pink-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-sm shadow-xl shadow-purple-900/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2.5 cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Generating Options...</span>
              </>
            ) : (
              <>
                <span className="text-base">✨</span>
                <span>Plan My Week</span>
              </>
            )}
          </button>

          <div className="flex items-center justify-between gap-2">
            <Link
              href="/student/constraints"
              className="flex-1 text-center px-3.5 py-2 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] font-medium transition"
            >
              ⚙️ Preferences
            </Link>

            {hasAppliedPlan && onRevertClick && (
              <button
                onClick={onRevertClick}
                className="px-3.5 py-2 rounded-xl bg-rose-50 dark:bg-red-950/20 hover:bg-rose-100 dark:hover:bg-red-950/40 border border-rose-200 dark:border-red-800/40 text-xs text-rose-700 dark:text-red-400 font-medium transition cursor-pointer"
                title="Remove study blocks applied for this week"
              >
                ↺ Revert Plan
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
