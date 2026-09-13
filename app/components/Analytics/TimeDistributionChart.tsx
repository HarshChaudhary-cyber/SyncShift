'use client';

import React from 'react';
import { HoursBreakdown, TimeDistributionData } from '@/lib/api';

interface TimeDistributionChartProps {
  distribution: TimeDistributionData | null;
  hours: HoursBreakdown | null;
  loading?: boolean;
}

export default function TimeDistributionChart({
  distribution,
  hours,
  loading,
}: TimeDistributionChartProps) {
  if (loading || !distribution || !hours) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl animate-pulse space-y-4">
        <div className="h-6 bg-[var(--bg-secondary)] rounded w-1/3" />
        <div className="h-8 bg-[var(--bg-secondary)] rounded-xl w-full" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-[var(--bg-secondary)] rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  const { class_percentage, work_percentage, study_percentage, free_percentage } = distribution;

  const categories = [
    {
      name: 'Class',
      hours: hours.class_hours,
      pct: class_percentage,
      color: 'bg-blue-500',
      text: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-500/10 border-blue-500/20',
      icon: '📚',
    },
    {
      name: 'Work',
      hours: hours.work_hours,
      pct: work_percentage,
      color: 'bg-emerald-500',
      text: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
      icon: '💼',
    },
    {
      name: 'Study',
      hours: hours.study_hours,
      pct: study_percentage,
      color: 'bg-purple-500',
      text: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-500/10 border-purple-500/20',
      icon: '📖',
    },
    {
      name: 'Free Time',
      hours: hours.free_hours,
      pct: free_percentage,
      color: 'bg-zinc-400 dark:bg-zinc-600',
      text: 'text-zinc-600 dark:text-zinc-300',
      bg: 'bg-zinc-500/10 border-zinc-500/20',
      icon: '☕',
    },
  ];

  return (
    <div
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl space-y-5"
      role="region"
      aria-label="Time Distribution Chart"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">⏱️</span>
          <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
            Time Distribution
          </h2>
        </div>
        <span className="text-xs text-[var(--text-muted)] font-mono">
          {hours.total_hours}h active / 105h waking
        </span>
      </div>

      {/* Segmented Distribution Bar */}
      <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl h-6 p-0.5 flex overflow-hidden shadow-inner">
        {class_percentage > 0 && (
          <div
            className="h-full bg-blue-500 transition-all duration-500 rounded-l-sm"
            style={{ width: `${class_percentage}%` }}
            title={`Class: ${class_percentage}%`}
          />
        )}
        {work_percentage > 0 && (
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${work_percentage}%` }}
            title={`Work: ${work_percentage}%`}
          />
        )}
        {study_percentage > 0 && (
          <div
            className="h-full bg-purple-500 transition-all duration-500"
            style={{ width: `${study_percentage}%` }}
            title={`Study: ${study_percentage}%`}
          />
        )}
        {free_percentage > 0 && (
          <div
            className="h-full bg-zinc-400 dark:bg-zinc-600 transition-all duration-500 rounded-r-sm"
            style={{ width: `${free_percentage}%` }}
            title={`Free: ${free_percentage}%`}
          />
        )}
      </div>

      {/* 4 Category Pill Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {categories.map((c) => (
          <div
            key={c.name}
            className={`p-3 rounded-xl border flex flex-col justify-between ${c.bg} transition hover:scale-[1.02]`}
          >
            <div className="flex items-center justify-between text-xs font-semibold mb-1">
              <span className="flex items-center gap-1">
                <span>{c.icon}</span>
                <span className={c.text}>{c.name}</span>
              </span>
              <span className="font-mono text-[11px] text-[var(--text-secondary)]">
                {c.pct}%
              </span>
            </div>
            <div className="text-lg sm:text-xl font-black text-[var(--text-primary)] font-mono">
              {c.hours}
              <span className="text-xs font-normal text-[var(--text-muted)] font-sans ml-0.5">
                h
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
