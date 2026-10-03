'use client';

import React from 'react';
import Link from 'next/link';
import { ScheduleContextSummary } from '@/lib/api';
import {useAuthContext} from '@/context/AuthContext';
import {isProfessor} from '@/lib/academic';

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
  const {user}=useAuthContext();
  const professor=isProfessor(user?.institution_role);
  return (
    <div className="ws-panel">
      {/* Background ambient decorative glow */}



      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-3 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-50 dark:bg-purple-500/10 border border-purple-200 dark:border-purple-500/20 text-purple-700 dark:text-purple-300 text-xs font-semibold">

            <span>Smart Weekly Planning</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--text-primary)]">
            {professor?'Teaching & personal planner':'Student planner'}
          </h1>

          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
            {professor?'Plan lecture preparation, grading, office hours and personal work around your fixed teaching commitments. Suggestions remain private.':'Plan study tasks and daily routines around official classes, shifts, availability and transition buffers.'} Review the proposed plan before applying it.
          </p>

          {/* Quick Context Summary Metrics */}
          {contextSummary && (
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">{contextSummary.enrolled_classes_count}</span>
                <span className="text-[var(--text-secondary)]">Class Meetings</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-amber-700 dark:text-amber-400 font-bold">{contextSummary.fixed_work_shifts_count}</span>
                <span className="text-[var(--text-secondary)]">Work Shifts</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
                <span className="text-purple-600 dark:text-purple-400 font-bold">{contextSummary.pending_tasks_count}</span>
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
            className="ws-button primary"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Generating Options...</span>
              </>
            ) : (
              <>

                <span>Plan My Week</span>
              </>
            )}
          </button>

          <div className="flex items-center justify-between gap-2">
            <Link
              href="/student/constraints"
              className="flex-1 text-center px-3.5 py-2 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--border-color)] border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] font-medium transition"
            >
              Planning preferences
            </Link>

            {hasAppliedPlan && onRevertClick && (
              <button
                onClick={onRevertClick}
                className="px-3.5 py-2 rounded-xl bg-rose-50 dark:bg-red-950/20 hover:bg-rose-100 dark:hover:bg-red-950/40 border border-rose-200 dark:border-red-800/40 text-xs text-rose-700 dark:text-red-400 font-medium transition cursor-pointer"
                title="Remove private sessions applied for this week"
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
