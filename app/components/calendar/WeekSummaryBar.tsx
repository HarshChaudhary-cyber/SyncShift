'use client';

import React from 'react';
import { useCalendar } from '@/context/CalendarContext';
import { useAuthContext } from '@/context/AuthContext';

export default function WeekSummaryBar() {
  const { totals, conflicts, blocks } = useCalendar();
  const { user } = useAuthContext();

  const limit = user?.weekly_work_hour_limit ?? 20;
  const isOver = totals.over_limit || totals.shift_hours > limit;

  // Calculate study hours from active blocks
  const studyHours = blocks
    .filter((b) => b.type === 'study' && !b.deleted)
    .reduce((acc, b) => {
      const s = b.start_time.split(':').map((v) => parseInt(v, 10));
      const e = b.end_time.split(':').map((v) => parseInt(v, 10));
      const dur = (e[0] * 60 + e[1]) - (s[0] * 60 + s[1]);
      return acc + Math.max(0, dur);
    }, 0) / 60;

  return (
    <div className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
      <div className="flex flex-wrap items-center gap-4 sm:gap-6">
        <span className="font-bold text-[var(--text-muted)] text-[11px] uppercase tracking-wider">
          This Week
        </span>

        {/* Classes */}
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-2xs shadow-blue-500/50" />
          <span className="text-[var(--text-secondary)]">Classes:</span>
          <span className="font-bold text-[var(--class-text)]">
            {totals.class_hours.toFixed(1)}h
          </span>
        </div>

        {/* Work Shifts & Visa Limit */}
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-2xs shadow-emerald-500/50" />
          <span className="text-[var(--text-secondary)]">Work:</span>
          <span
            className={`font-bold ${
              isOver ? 'text-rose-600 dark:text-rose-400' : 'text-[var(--shift-text)]'
            }`}
          >
            {totals.shift_hours.toFixed(1)}h
            <span className="text-[var(--text-muted)] font-normal text-[11px]"> / {limit}h limit</span>
          </span>
        </div>

        {/* Study Tasks if any */}
        {studyHours > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-2xs shadow-purple-500/50" />
            <span className="text-[var(--text-secondary)]">Study:</span>
            <span className="font-bold text-[var(--study-text)]">
              {studyHours.toFixed(1)}h
            </span>
          </div>
        )}

        {/* Est. Earnings */}
        {totals.expected_earnings > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-emerald-600 dark:text-emerald-400 font-bold">$</span>
            <span className="text-[var(--text-secondary)]">Earnings:</span>
            <span className="font-bold text-[var(--text-primary)]">
              ${totals.expected_earnings.toFixed(2)}
            </span>
          </div>
        )}

        {/* Conflicts Count */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              conflicts.length > 0 ? 'bg-rose-500 animate-pulse' : 'bg-emerald-500'
            }`}
          />
          <span className="text-[var(--text-secondary)]">Conflicts:</span>
          <span
            className={`font-bold ${
              conflicts.length > 0
                ? 'text-rose-600 dark:text-rose-400'
                : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {conflicts.length === 0 ? '0' : `${conflicts.length} conflict${conflicts.length > 1 ? 's' : ''}`}
          </span>
        </div>
      </div>

      {/* Over Limit Alert Pill */}
      {isOver && (
        <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/40 text-rose-600 dark:text-rose-400 text-[11px] font-bold animate-pulse">
          <span>⚠️</span>
          <span>Visa Limit Exceeded ({totals.shift_hours.toFixed(1)}h / {limit}h)</span>
        </div>
      )}
    </div>
  );
}
