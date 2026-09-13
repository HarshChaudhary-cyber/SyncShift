'use client';

import React from 'react';
import { WorkLimitAnalytics } from '@/lib/api';

interface WeeklyHoursCardProps {
  workLimit: WorkLimitAnalytics | null;
  loading?: boolean;
}

export default function WeeklyHoursCard({
  workLimit,
  loading,
}: WeeklyHoursCardProps) {
  if (loading || !workLimit) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl animate-pulse space-y-4">
        <div className="h-6 bg-[var(--bg-secondary)] rounded w-1/3" />
        <div className="h-8 bg-[var(--bg-secondary)] rounded-xl" />
        <div className="h-4 bg-[var(--bg-secondary)] rounded w-1/2" />
      </div>
    );
  }

  const { configured, used, remaining, percentage, over_limit, over_hours } = workLimit;

  return (
    <div
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl space-y-4 flex flex-col justify-between"
      role="region"
      aria-label="Work-Hour Utilization"
    >
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xl">💼</span>
            <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
              Work-Hour Utilization
            </h2>
          </div>
          <span
            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
              over_limit
                ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30'
                : percentage >= 90
                ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30'
                : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
            }`}
          >
            {percentage}%
          </span>
        </div>

        {/* Big numbers */}
        <div className="flex items-baseline justify-between mb-3">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-black text-[var(--text-primary)] font-mono">
              {used}
            </span>
            <span className="text-sm text-[var(--text-secondary)] font-mono">
              / {configured}h
            </span>
          </div>
          <span className="text-xs font-medium text-[var(--text-secondary)]">
            {over_limit ? (
              <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-1">
                <span>⚠️</span>
                <span>{over_hours}h over limit</span>
              </span>
            ) : (
              <span>{remaining}h remaining</span>
            )}
          </span>
        </div>

        {/* Utilization Bar */}
        <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-full h-3 sm:h-3.5 p-0.5 mb-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${
              over_limit
                ? 'bg-rose-500'
                : percentage >= 90
                ? 'bg-amber-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, Math.max(4, percentage))}%` }}
            role="progressbar"
            aria-valuenow={percentage}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      {/* Footer warning or note */}
      <div className="pt-2 border-t border-[var(--border-color)]">
        {over_limit ? (
          <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
            <span>⚠️</span>
            <span>You have exceeded your configured weekly limit by {over_hours} hours.</span>
          </div>
        ) : (
          <p className="text-[11px] text-[var(--text-muted)]">
            Configured limit is set in your profile settings.
          </p>
        )}
      </div>
    </div>
  );
}
