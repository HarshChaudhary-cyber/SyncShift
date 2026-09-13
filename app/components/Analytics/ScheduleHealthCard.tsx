'use client';

import React, { useState } from 'react';
import { ScheduleHealthData } from '@/lib/api';
import ImproveWeekModal from './ImproveWeekModal';

interface ScheduleHealthCardProps {
  health: ScheduleHealthData | null;
  loading?: boolean;
}

export default function ScheduleHealthCard({
  health,
  loading,
}: ScheduleHealthCardProps) {
  const [modalOpen, setModalOpen] = useState(false);

  if (loading || !health) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl animate-pulse space-y-4">
        <div className="flex justify-between items-center">
          <div className="h-6 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="h-6 bg-[var(--bg-secondary)] rounded w-16" />
        </div>
        <div className="h-4 bg-[var(--bg-secondary)] rounded-full w-full" />
        <div className="space-y-2 pt-2">
          <div className="h-4 bg-[var(--bg-secondary)] rounded w-3/4" />
          <div className="h-4 bg-[var(--bg-secondary)] rounded w-2/3" />
        </div>
      </div>
    );
  }

  const { score, category, summary, factors } = health;

  // Category Color Scheme
  const getCategoryStyles = (cat: string, s: number) => {
    if (s >= 90) {
      return {
        badge: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
        progress: 'bg-emerald-500',
        text: 'text-emerald-600 dark:text-emerald-400',
        icon: '🌟',
      };
    }
    if (s >= 75) {
      return {
        badge: 'bg-teal-500/15 text-teal-600 dark:text-teal-400 border-teal-500/30',
        progress: 'bg-teal-500',
        text: 'text-teal-600 dark:text-teal-400',
        icon: '⚡',
      };
    }
    if (s >= 60) {
      return {
        badge: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
        progress: 'bg-amber-500',
        text: 'text-amber-600 dark:text-amber-400',
        icon: '⚖️',
      };
    }
    if (s >= 40) {
      return {
        badge: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30',
        progress: 'bg-orange-500',
        text: 'text-orange-600 dark:text-orange-400',
        icon: '⚠️',
      };
    }
    return {
      badge: 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30',
      progress: 'bg-rose-500',
      text: 'text-rose-600 dark:text-rose-400',
      icon: '🚨',
    };
  };

  const styles = getCategoryStyles(category, score);

  return (
    <>
      <div
        className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl relative overflow-hidden flex flex-col justify-between"
        role="region"
        aria-label="Schedule Health Score"
      >
        <div>
          {/* Header Row */}
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-xl">🩺</span>
              <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] tracking-tight">
                Schedule Health
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1 ${styles.badge}`}
              >
                <span>{styles.icon}</span>
                <span>{category}</span>
              </span>
              <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
                {score}
                <span className="text-xs font-normal text-[var(--text-muted)] font-sans">
                  /100
                </span>
              </span>
            </div>
          </div>

          {/* Progress Gauge */}
          <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-full h-3 sm:h-3.5 p-0.5 mb-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${styles.progress}`}
              style={{ width: `${Math.max(4, score)}%` }}
              role="progressbar"
              aria-valuenow={score}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>

          {/* Subtitle / summary */}
          <p className="text-xs text-[var(--text-secondary)] mb-4 leading-relaxed">
            {summary}
          </p>

          {/* Factors Breakdown: Checkmarks and Warnings */}
          <div className="space-y-2 mb-5">
            {factors.slice(0, 4).map((factor, idx) => (
              <div
                key={idx}
                className={`text-xs flex items-center gap-2 p-2 rounded-lg border transition ${
                  factor.type === 'positive'
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-800 dark:text-emerald-300'
                    : 'bg-amber-500/5 border-amber-500/20 text-amber-800 dark:text-amber-300'
                }`}
              >
                <span className="font-bold text-sm shrink-0">
                  {factor.type === 'positive' ? '✓' : '⚠'}
                </span>
                <span className="truncate">{factor.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Button: Improve my week */}
        <div className="pt-2 border-t border-[var(--border-color)] flex items-center justify-between gap-3">
          <span className="text-[11px] text-[var(--text-muted)]">
            Productivity & workload indicator
          </span>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-indigo-900/30 flex items-center gap-1.5"
          >
            <span>💡</span>
            <span>Improve my week</span>
          </button>
        </div>
      </div>

      <ImproveWeekModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        health={health}
      />
    </>
  );
}
