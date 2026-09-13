'use client';

import React from 'react';
import { DashboardWeek } from '@/lib/api';

interface WeekSummaryCardProps {
  week: DashboardWeek | null;
  studyHours?: number;
  currency?: string;
  loading?: boolean;
}

export default function WeekSummaryCard({
  week,
  studyHours,
  currency = '₹',
  loading,
}: WeekSummaryCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-lg flex flex-col justify-between h-full min-h-[300px] animate-pulse">
        <div className="space-y-4">
          <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="h-20 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-20 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-20 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-20 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-20 bg-[var(--bg-secondary)] rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  const shiftHours = week?.total_shift_hours ?? 0;
  const classHours = week?.total_class_hours ?? 0;
  const earnings = week?.expected_earnings ?? 0;
  const conflictCount = week?.conflict_count ?? 0;
  const overWorkLimit = week?.over_work_limit ?? false;
  const workLimit = week?.work_limit ?? 20;
  const showStudy = studyHours !== undefined;

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[300px]">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>📊</span>
            <span>Weekly Summary</span>
          </h2>
          {week?.start && week?.end && (
            <span className="text-[11px] font-mono text-[var(--text-secondary)] bg-[var(--bg-secondary)] border border-[var(--border-color)] px-2 py-0.5 rounded">
              {week.start} – {week.end}
            </span>
          )}
        </div>

        {/* Stat Tiles Grid */}
        <div className={`grid gap-3 ${showStudy ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2'}`}>
          {/* Tile 1: Class Hours */}
          <div className="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-color)] transition">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
              📚 Classes
            </span>
            <div className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] font-mono">
              {classHours}<span className="text-xs font-normal text-[var(--text-muted)] ml-0.5">h</span>
            </div>
            <span className="text-[10px] text-[var(--text-muted)] block mt-0.5">
              Scheduled lectures
            </span>
          </div>

          {/* Tile 2: Shift Hours */}
          <div className="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-color)] transition">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
              💼 Work
            </span>
            <div className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] font-mono">
              {shiftHours}<span className="text-xs font-normal text-[var(--text-muted)] ml-0.5">h</span>
            </div>
            <span className="text-[10px] text-[var(--text-muted)] block mt-0.5 font-mono">
              Limit: {workLimit}h
            </span>
          </div>

          {/* Tile 3: Study Hours (if available) */}
          {showStudy && (
            <div className="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-color)] transition">
              <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
                📖 Study
              </span>
              <div className="text-xl sm:text-2xl font-bold text-purple-400 font-mono">
                {studyHours}<span className="text-xs font-normal text-[var(--text-muted)] ml-0.5">h</span>
              </div>
              <span className="text-[10px] text-[var(--text-muted)] block mt-0.5">
                Planned goals
              </span>
            </div>
          )}

          {/* Tile 4: Conflicts */}
          <div
            className={`p-3.5 rounded-xl border transition ${
              conflictCount > 0
                ? 'bg-[var(--conflict-bg)] border-[var(--conflict-border)]'
                : 'bg-[var(--bg-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-color)]'
            }`}
          >
            <span
              className={`text-[11px] font-medium uppercase tracking-wider block mb-1 ${
                conflictCount > 0 ? 'text-rose-600 dark:text-rose-400 font-semibold' : 'text-[var(--text-secondary)]'
              }`}
            >
              {conflictCount > 0 ? '⚠️ Conflicts' : '✓ Conflicts'}
            </span>
            <div
              className={`text-xl sm:text-2xl font-bold font-mono ${
                conflictCount > 0 ? 'text-rose-600 dark:text-rose-300' : 'text-[var(--text-primary)]'
              }`}
            >
              {conflictCount}
            </div>
            <span
              className={`text-[10px] block mt-0.5 ${
                conflictCount > 0 ? 'text-rose-600/80 dark:text-rose-400/80' : 'text-[var(--text-muted)]'
              }`}
            >
              {conflictCount > 0 ? 'Clashes detected' : 'Clear schedule'}
            </span>
          </div>

          {/* Tile 5: Earnings */}
          <div className="p-3.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-color)] transition">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
              💰 Earnings
            </span>
            <div className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] font-mono truncate" suppressHydrationWarning>
              {currency}{earnings.toLocaleString()}
            </div>
            <span className="text-[10px] text-[var(--text-muted)] block mt-0.5">
              Estimated wage
            </span>
          </div>
        </div>
      </div>

      {/* Warning banner inside card if over limit */}
      {overWorkLimit && (
        <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 text-xs flex items-center gap-2">
          <span className="text-base shrink-0">⚠️</span>
          <span className="leading-snug">
            <strong>{shiftHours}h/week</strong> — over your {workLimit}h work limit
          </span>
        </div>
      )}
    </div>
  );
}
