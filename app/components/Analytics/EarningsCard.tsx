'use client';

import React from 'react';
import { EarningsAnalytics } from '@/lib/api';

interface EarningsCardProps {
  earnings: EarningsAnalytics | null;
  loading?: boolean;
}

export default function EarningsCard({
  earnings,
  loading,
}: EarningsCardProps) {
  if (loading || !earnings) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl animate-pulse space-y-4">
        <div className="h-6 bg-[var(--bg-secondary)] rounded w-1/3" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-16 bg-[var(--bg-secondary)] rounded-xl" />
          <div className="h-16 bg-[var(--bg-secondary)] rounded-xl" />
        </div>
      </div>
    );
  }

  const { currency, currency_symbol, estimated_week, estimated_month, missing_wage_shifts } = earnings;

  return (
    <div
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl space-y-4 flex flex-col justify-between"
      role="region"
      aria-label="Earnings Analytics"
    >
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">💰</span>
            <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
              Estimated Shift Earnings
            </h2>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
            {currency}
          </span>
        </div>

        {/* 2 Tiles: This Week and Projected Month */}
        <div className="grid grid-cols-2 gap-3 mb-2">
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400 block mb-1">
              This Week
            </span>
            <div className="text-xl sm:text-2xl font-black text-amber-600 dark:text-amber-300 font-mono">
              {currency_symbol}{estimated_week.toLocaleString()}
            </div>
            <span className="text-[10px] text-amber-700/70 dark:text-amber-400/70 block mt-0.5">
              Scheduled shifts
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 block mb-1">
              Projected Month
            </span>
            <div className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-300 font-mono">
              {currency_symbol}{estimated_month.toLocaleString()}
            </div>
            <span className="text-[10px] text-emerald-700/70 dark:text-emerald-400/70 block mt-0.5">
              ~4.33 weeks avg
            </span>
          </div>
        </div>
      </div>

      {/* Footer warning if missing wage */}
      <div className="pt-2 border-t border-[var(--border-color)]">
        {missing_wage_shifts > 0 ? (
          <p className="text-[11px] text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
            <span>ℹ️</span>
            <span>
              Hourly wage unconfigured for {missing_wage_shifts} {missing_wage_shifts === 1 ? 'shift' : 'shifts'}.
            </span>
          </p>
        ) : (
          <p className="text-[11px] text-[var(--text-muted)]">
            Calculated from scheduled shift hours × hourly wage rate.
          </p>
        )}
      </div>
    </div>
  );
}
