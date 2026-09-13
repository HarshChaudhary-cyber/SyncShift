'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, AnalyticsData, StudyTask } from '@/lib/api';

interface YourWeekCardProps {
  onPlanStudy?: () => void;
}

export default function YourWeekCard({ onPlanStudy }: YourWeekCardProps) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    Promise.all([
      api.getAnalytics().catch(() => null),
      api.getTasks().catch(() => []),
    ]).then(([analyticsData, tasksData]) => {
      if (!isMounted) return;
      if (analyticsData) setAnalytics(analyticsData);
      if (tasksData) setTasks(tasksData);
      setLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 animate-pulse">
        <div className="h-5 w-32 bg-[var(--bg-secondary)] rounded-md mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-[var(--bg-secondary)] rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!analytics) return null;

  const health = analytics.health;
  const nextTask = tasks.find(
    (t) =>
      t.status !== 'done' &&
      (t.completed_hours ?? t.hours_done ?? 0) < t.total_hours_required
  );

  const getHealthBadgeStyle = (category: string) => {
    switch (category) {
      case 'Excellent':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'Healthy':
        return 'bg-teal-500/10 text-teal-400 border-teal-500/30';
      case 'Moderate':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'Needs attention':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      default:
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚡</span>
          <h2 className="text-base font-bold text-[var(--text-primary)]">Your Week</h2>
          <span
            className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getHealthBadgeStyle(
              health.category
            )}`}
          >
            {health.category}
          </span>
        </div>

        <Link
          href="/analytics"
          className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 self-start sm:self-auto"
        >
          <span>View Analytics</span>
          <span>→</span>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-4">
        {/* Metric 1: Health */}
        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider block mb-1">
            Schedule Health
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {health.score}
            </span>
            <span className="text-xs text-[var(--text-muted)] font-mono">/ 100</span>
          </div>
        </div>

        {/* Metric 2: Work Limit */}
        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider block mb-1">
            Work
          </span>
          <div className="flex items-baseline gap-1.5">
            <span
              className={`text-xl sm:text-2xl font-black font-mono ${
                analytics.work_limit.over_limit
                  ? 'text-rose-400'
                  : 'text-[var(--text-primary)]'
              }`}
            >
              {analytics.work_limit.used}
            </span>
            <span className="text-xs text-[var(--text-muted)] font-mono">
              / {analytics.work_limit.configured}h
            </span>
          </div>
        </div>

        {/* Metric 3: Study */}
        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider block mb-1">
            Study
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-xl sm:text-2xl font-black text-purple-400 font-mono">
              {analytics.hours.study_hours}
            </span>
            <span className="text-xs text-[var(--text-muted)] font-mono">h planned</span>
          </div>
        </div>

        {/* Metric 4: Conflicts */}
        <div className="p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl">
          <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider block mb-1">
            Conflicts
          </span>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-xl sm:text-2xl font-black font-mono ${
                analytics.conflicts.hard > 0
                  ? 'text-rose-400'
                  : analytics.conflicts.warning > 0
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {analytics.conflicts.total}
            </span>
            <span className="text-xs text-[var(--text-muted)] font-mono">
              {analytics.conflicts.total === 0 ? '✓ clear' : 'issues'}
            </span>
          </div>
        </div>
      </div>

      {/* Next Recommendation / Action Row */}
      <div className="pt-3 border-t border-[var(--border-color)] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shrink-0 text-sm">
            📚
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] block">
              Next recommendation
            </span>
            {nextTask ? (
              <p className="text-xs sm:text-sm font-semibold text-[var(--text-primary)]">
                {nextTask.title}{' '}
                <span className="text-purple-400 font-normal">
                  ·{' '}
                  {nextTask.preferred_duration
                    ? `${nextTask.preferred_duration / 60}h`
                    : '1.5h'}{' '}
                  suggested before deadline
                </span>
              </p>
            ) : (
              <p className="text-xs sm:text-sm text-[var(--text-secondary)]">
                All study tasks on track. Keep up the balanced routine!
              </p>
            )}
          </div>
        </div>

        <Link
          href="/planner"
          onClick={onPlanStudy}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold transition shadow-sm flex items-center justify-center gap-1.5 self-start sm:self-auto cursor-pointer"
        >
          <span>Plan study</span>
          <span>→</span>
        </Link>
      </div>
    </div>
  );
}
