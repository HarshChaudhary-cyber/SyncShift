'use client';

import React from 'react';
import { HealthFactor, ScheduleHealthData } from '@/lib/api';
import Link from 'next/link';

interface ImproveWeekModalProps {
  isOpen: boolean;
  onClose: () => void;
  health: ScheduleHealthData | null;
}

export default function ImproveWeekModal({
  isOpen,
  onClose,
  health,
}: ImproveWeekModalProps) {
  if (!isOpen || !health) return null;

  const warnings = health.factors.filter((f) => f.type === 'warning');
  const positives = health.factors.filter((f) => f.type === 'positive');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--modal-overlay)] backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="improve-week-title"
    >
      <div
        className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5 text-[var(--text-primary)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🌱</span>
              <h2 id="improve-week-title" className="text-lg font-bold text-[var(--text-primary)]">
                Improve Your Week
              </h2>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Deterministic workload diagnosis and actionable recommendations to balance your schedule.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1 rounded-lg hover:bg-[var(--bg-secondary)] transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Current Score Summary */}
        <div className="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-between">
          <div>
            <span className="text-xs text-[var(--text-secondary)] block">Schedule Health Score</span>
            <span className="text-2xl font-black text-[var(--text-primary)]">
              {health.score} <span className="text-sm font-normal text-[var(--text-muted)]">/ 100</span>
            </span>
          </div>
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
            {health.category}
          </span>
        </div>

        {/* Current Bottlenecks & Warnings */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            Identified Bottlenecks ({warnings.length})
          </h3>
          {warnings.length === 0 ? (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
              <span>✓</span>
              <span>No critical schedule bottlenecks detected this week!</span>
            </div>
          ) : (
            <ul className="space-y-1.5">
              {warnings.map((w, idx) => (
                <li
                  key={idx}
                  className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2"
                >
                  <span className="text-sm shrink-0">⚠️</span>
                  <span>{w.text}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Actionable Recommendations */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            Recommended Actions
          </h3>
          <ul className="space-y-2">
            {health.improvements.map((imp, idx) => (
              <li
                key={idx}
                className="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] flex items-start gap-2.5"
              >
                <span className="font-bold text-indigo-500 mt-0.5">{idx + 1}.</span>
                <span className="leading-relaxed">{imp}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Navigation Quick Action */}
        <div className="pt-2 flex items-center justify-end gap-3 border-t border-[var(--border-color)]">
          <Link
            href="/planner"
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-indigo-900/30 flex items-center gap-1.5"
          >
            <span>📖</span>
            <span>Open Study Planner</span>
          </Link>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl text-xs font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
