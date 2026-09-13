'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardAlert, WorkLimitAnalytics } from '@/lib/api';

interface AlertsBannerProps {
  alerts?: DashboardAlert[];
  conflicts?: { hard: number; warning: number; total: number } | null;
  work?: WorkLimitAnalytics | null;
  adaptiveState?: string | null;
}

export default function AlertsBanner({
  alerts = [],
  conflicts,
  work,
  adaptiveState,
}: AlertsBannerProps) {
  const router = useRouter();
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Filter out dismissed alerts
  const visibleAlerts = alerts.filter((a) => !dismissedIds.has(a.id));

  // Determine if problems exist
  const hardConflicts = conflicts?.hard ?? 0;
  const warningConflicts = conflicts?.warning ?? 0;
  const isOverWork = work?.over_limit ?? false;
  const hasAlerts = visibleAlerts.length > 0;
  const isNearWorkLimit = adaptiveState === 'near_work_limit';

  const hasProblems =
    hardConflicts > 0 ||
    warningConflicts > 0 ||
    isOverWork ||
    hasAlerts ||
    adaptiveState === 'conflicts' ||
    adaptiveState === 'over_work_limit';

  // Do not show attention banner for new users as adaptive banner takes priority
  if (adaptiveState === 'new_user') return null;

  const handleDismiss = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDismissedIds((prev) => new Set(prev).add(id));
  };

  if (!hasProblems) {
    return (
      <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-800 dark:text-emerald-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 transition-all">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-base shrink-0">
            ✓
          </div>
          <div>
            <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-100 flex items-center gap-2">
              You're on track
            </h3>
            <p className="text-xs text-emerald-700 dark:text-emerald-300">
              No unresolved conflicts · Work hours within configured limit
            </p>
          </div>
        </div>
        <button
          onClick={() => router.push('/calendar')}
          className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition self-start sm:self-auto cursor-pointer shadow-sm"
        >
          View Calendar →
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3 mb-6">
      {/* Primary Attention Needed Summary Card */}
      <div className="p-4 sm:p-5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-900 dark:text-rose-100 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-rose-600 dark:text-rose-300">
              Attention needed
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
            {hardConflicts > 0 && (
              <span className="px-2.5 py-1 rounded-lg bg-rose-500/20 border border-rose-500/40 text-rose-700 dark:text-rose-200 flex items-center gap-1.5">
                🔴 {hardConflicts} hard conflict{hardConflicts > 1 ? 's' : ''}
              </span>
            )}
            {warningConflicts > 0 && (
              <span className="px-2.5 py-1 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-800 dark:text-amber-200 flex items-center gap-1.5">
                🟡 {warningConflicts} warning{warningConflicts > 1 ? 's' : ''}
              </span>
            )}
            {work && (
              <span
                className={`px-2.5 py-1 rounded-lg border flex items-center gap-1.5 ${
                  work.over_limit
                    ? 'bg-rose-500/20 border-rose-500/40 text-rose-700 dark:text-rose-200'
                    : isNearWorkLimit
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-800 dark:text-amber-200'
                    : 'bg-neutral-500/10 border-neutral-500/20 text-[var(--text-secondary)]'
                }`}
              >
                ⚠ Work hours: {work.used} / {work.configured}h
                {work.over_limit && ` (${work.over_hours}h over limit)`}
              </span>
            )}
          </div>
        </div>

        <button
          onClick={() => router.push('/calendar')}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold transition shadow-md shadow-rose-900/30 flex items-center justify-center gap-1 self-start sm:self-auto cursor-pointer"
        >
          <span>Review</span>
          <span>→</span>
        </button>
      </div>

      {/* Individual Specific Alerts (if any) */}
      {visibleAlerts.map((alert) => {
        const isConflict = alert.type === 'conflict' || alert.severity === 'hard';

        return (
          <div
            key={alert.id}
            className={`p-3.5 rounded-xl border shadow-sm flex items-center justify-between gap-3 transition-all ${
              isConflict
                ? 'bg-rose-500/10 border-rose-500/40 text-rose-800 dark:text-rose-200'
                : 'bg-amber-500/10 border-amber-500/40 text-amber-800 dark:text-amber-200'
            }`}
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-lg shrink-0">{isConflict ? '🔴' : '⚠️'}</span>
              <p className="text-xs font-semibold truncate sm:whitespace-normal">
                {alert.message}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => router.push('/calendar')}
                className={`text-xs font-bold px-2.5 py-1 rounded-lg border transition cursor-pointer flex items-center gap-1 ${
                  isConflict
                    ? 'bg-rose-600 hover:bg-rose-500 text-white border-transparent'
                    : 'bg-amber-600 hover:bg-amber-500 text-white border-transparent'
                }`}
              >
                <span>View</span>
                <span>→</span>
              </button>

              <button
                onClick={(e) => handleDismiss(alert.id, e)}
                title="Dismiss alert"
                className="p-1 rounded-lg hover:bg-neutral-500/15 text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition cursor-pointer"
                aria-label="Dismiss alert"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
