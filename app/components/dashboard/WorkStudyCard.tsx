'use client';

import React from 'react';
import Link from 'next/link';
import { WorkLimitAnalytics } from '@/lib/api';

interface DashboardStudyInfo {
  planned_hours: number;
  target_hours: number;
  remaining_hours: number;
  pending_tasks_count: number;
  upcoming_task: {
    id: number;
    title: string;
    deadline: string;
    priority: string;
  } | null;
}

interface WorkStudyCardProps {
  work?: WorkLimitAnalytics | null;
  study?: DashboardStudyInfo | null;
  loading?: boolean;
  onAddStudyGoal?: () => void;
}

export default function WorkStudyCard({
  work,
  study,
  loading,
  onAddStudyGoal,
}: WorkStudyCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[260px] animate-pulse space-y-4">
        <div className="space-y-3">
          <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="h-8 bg-[var(--bg-secondary)] rounded w-1/2" />
          <div className="h-2 bg-[var(--bg-secondary)] rounded w-full" />
        </div>
        <div className="space-y-3 pt-4 border-t border-[var(--border-color)]">
          <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="h-8 bg-[var(--bg-secondary)] rounded w-2/3" />
        </div>
      </div>
    );
  }

  // Work parameters
  const workUsed = work?.used ?? 0;
  const workConfigured = work?.configured ?? 20;
  const workOverLimit = work?.over_limit ?? false;
  const workOverHours = work?.over_hours ?? 0;
  const workRemaining = work?.remaining ?? Math.max(0, workConfigured - workUsed);
  const workPct = Math.min(100, Math.round((workUsed / (workConfigured || 1)) * 100));

  // Study parameters
  const studyPlanned = study?.planned_hours ?? 0;
  const studyTarget = study?.target_hours ?? 8;
  const studyRemaining = study?.remaining_hours ?? Math.max(0, studyTarget - studyPlanned);
  const upcomingTask = study?.upcoming_task;

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[260px] space-y-5">
      {/* ── Section 1: Work Capacity ── */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase flex items-center gap-1.5">
            <span>💼</span>
            <span>Work This Week</span>
          </h3>
          <span className="text-xs font-semibold text-[var(--text-muted)] font-mono">
            Limit: {workConfigured}h/wk
          </span>
        </div>

        <div className="flex items-baseline justify-between gap-2 mb-2">
          <div className="flex items-baseline gap-1.5">
            <span
              className={`text-2xl sm:text-3xl font-black font-mono ${
                workOverLimit ? 'text-rose-500' : 'text-[var(--text-primary)]'
              }`}
            >
              {workUsed}
            </span>
            <span className="text-xs text-[var(--text-muted)] font-mono">/ {workConfigured}h</span>
          </div>

          <span
            className={`text-xs font-bold px-2 py-0.5 rounded-md ${
              workOverLimit
                ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30'
                : workPct >= 80
                ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30'
                : 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30'
            }`}
          >
            {workPct}%
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-[var(--bg-secondary)] rounded-full h-2 overflow-hidden mb-1.5">
          <div
            className={`h-full rounded-full transition-all ${
              workOverLimit
                ? 'bg-rose-500'
                : workPct >= 80
                ? 'bg-amber-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, workPct)}%` }}
          />
        </div>

        <p className="text-[11px] text-[var(--text-muted)]">
          {workOverLimit ? (
            <span className="text-rose-600 dark:text-rose-400 font-semibold">
              ⚠ {workOverHours}h over configured limit
            </span>
          ) : (
            <span>{workRemaining}h capacity remaining</span>
          )}
        </p>
      </div>

      {/* ── Section 2: Study Summary ── */}
      <div className="pt-4 border-t border-[var(--border-color)]">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase flex items-center gap-1.5">
            <span>📖</span>
            <span>Study This Week</span>
          </h3>
          <span className="text-xs text-[var(--text-muted)] font-mono">
            {studyPlanned} / {studyTarget}h planned
          </span>
        </div>

        {upcomingTask ? (
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold text-purple-700 dark:text-purple-400 block tracking-wider">
                Upcoming Goal · Due {upcomingTask.deadline}
              </span>
              <p className="text-xs font-semibold text-[var(--text-primary)] truncate">
                {upcomingTask.title}
              </p>
              <span className="text-[10px] text-[var(--text-muted)]">
                {studyRemaining > 0 ? `${studyRemaining}h remaining` : 'Target met'}
              </span>
            </div>

            <Link
              href="/student/planner"
              className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-bold transition shrink-0 cursor-pointer shadow-sm"
            >
              Plan study
            </Link>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3 py-1">
            <div>
              <p className="text-xs text-[var(--text-secondary)] font-medium">
                No study goals yet.
              </p>
              <p className="text-[10px] text-[var(--text-muted)]">
                Create a goal and SyncShift can suggest study sessions.
              </p>
            </div>
            {onAddStudyGoal ? (
              <button
                type="button"
                onClick={onAddStudyGoal}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold transition shrink-0 cursor-pointer"
              >
                Create study goal
              </button>
            ) : (
              <Link
                href="/student/planner"
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold transition shrink-0"
              >
                Create study goal
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
