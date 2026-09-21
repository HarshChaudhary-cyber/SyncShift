'use client';

import React from 'react';
import Link from 'next/link';
import { ScheduleHealthData } from '@/lib/api';

interface ScheduleHealthCardProps {
  health?: ScheduleHealthData | null;
  loading?: boolean;
}

export default function ScheduleHealthCard({ health, loading }: ScheduleHealthCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[260px] animate-pulse">
        <div className="space-y-4">
          <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="h-10 bg-[var(--bg-secondary)] rounded w-1/2" />
          <div className="space-y-2">
            <div className="h-4 bg-[var(--bg-secondary)] rounded w-full" />
            <div className="h-4 bg-[var(--bg-secondary)] rounded w-4/5" />
          </div>
        </div>
        <div className="h-8 bg-[var(--bg-secondary)] rounded w-28 mt-4" />
      </div>
    );
  }

  if (!health) return null;

  const score = health.score ?? 100;
  const category = health.category || 'Healthy';
  const factors = health.factors || [];

  const getBadgeClass = (cat: string) => {
    switch (cat) {
      case 'Excellent':
        return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30';
      case 'Healthy':
        return 'bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-200 dark:border-teal-500/30';
      case 'Moderate':
        return 'bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-400 border-amber-200 dark:border-amber-500/30';
      case 'Needs attention':
        return 'bg-orange-50 dark:bg-orange-500/10 text-orange-800 dark:text-orange-400 border-orange-200 dark:border-orange-500/30';
      default:
        return 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/30';
    }
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[260px]">
      <div>
        {/* Top Header */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <h3 className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase flex items-center gap-1.5">
            <span>🛡️</span>
            <span>Schedule Health</span>
          </h3>
          <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getBadgeClass(category)}`}>
            {category}
          </span>
        </div>

        {/* Score Display */}
        <div className="flex items-baseline gap-2 mb-4">
          <span className="text-3xl sm:text-4xl font-black text-[var(--text-primary)] font-mono">
            {score}
          </span>
          <span className="text-sm font-semibold text-[var(--text-muted)] font-mono">/ 100</span>
        </div>

        {/* 2–3 Meaningful Factors */}
        <div className="space-y-2 mb-4">
          {factors.slice(0, 3).map((factor, idx) => {
            const isPos = factor.type === 'positive';
            const isWarn = factor.type === 'warning';

            return (
              <div
                key={idx}
                className="flex items-start gap-2 text-xs leading-relaxed"
              >
                <span className="shrink-0 mt-0.5">
                  {isPos ? '✓' : isWarn ? '⚠' : 'ℹ'}
                </span>
                <span
                  className={
                    isPos
                      ? 'text-emerald-700 dark:text-emerald-300'
                      : isWarn
                      ? 'text-amber-700 dark:text-amber-300'
                      : 'text-[var(--text-secondary)]'
                  }
                >
                  {factor.text}
                </span>
              </div>
            );
          })}
          {factors.length === 0 && (
            <p className="text-xs text-[var(--text-muted)]">
              ✓ Balanced timetable with no major schedule penalties detected.
            </p>
          )}
        </div>
      </div>

      {/* Action CTA */}
      <div className="pt-3 border-t border-[var(--border-color)] flex items-center justify-between">
        <span className="text-xs text-[var(--text-muted)]">
          {health.summary || 'Based on conflicts and workload'}
        </span>
        <Link
          href="/analytics"
          className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition flex items-center gap-1 cursor-pointer"
        >
          <span>Improve my week</span>
          <span>→</span>
        </Link>
      </div>
    </div>
  );
}
