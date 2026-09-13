'use client';

import React from 'react';
import { DashboardNextUp } from '@/lib/api';

import Link from 'next/link';

interface NextUpCardProps {
  nextUp: DashboardNextUp | null;
  loading?: boolean;
}

export default function NextUpCard({ nextUp, loading }: NextUpCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-lg flex flex-col justify-between h-full min-h-[220px] animate-pulse">
        <div className="space-y-3">
          <div className="h-4 bg-[var(--bg-secondary)] rounded w-1/3" />
          <div className="h-8 bg-[var(--bg-secondary)] rounded w-3/4" />
          <div className="h-4 bg-[var(--bg-secondary)] rounded w-1/2" />
        </div>
        <div className="h-6 bg-[var(--bg-secondary)] rounded w-2/5 mt-6" />
      </div>
    );
  }

  if (!nextUp) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-lg flex flex-col justify-between h-full min-h-[220px] relative overflow-hidden">
        {/* Subtle decorative glow */}
        <div className="absolute -right-8 -top-8 w-28 h-28 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="space-y-2 relative z-10">
          <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-emerald-500 dark:text-emerald-400 uppercase">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            NEXT UP
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] pt-2">
            You're done for today.
          </h2>
          <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed pt-1">
            No more scheduled events. Rest up or plan ahead in the calendar.
          </p>
        </div>

        <div className="pt-4 border-t border-[var(--border-color)] flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>All caught up</span>
          <Link
            href="/calendar"
            className="text-xs font-semibold text-indigo-500 hover:text-indigo-400 transition flex items-center gap-1 cursor-pointer"
          >
            <span>View calendar</span>
            <span>→</span>
          </Link>
        </div>
      </div>
    );
  }

  const { block, minutes_until, label } = nextUp;
  const isShift = block.type === 'shift';
  const isStudy = block.type === 'study';
  const typeBadgeColor = isStudy
    ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20'
    : isShift
    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
    : 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
  const barColor = block.color || (isStudy ? '#8B5CF6' : isShift ? '#10B981' : '#3B82F6');

  // Countdown text formatting
  let countdownDisplay = `Starts in ${minutes_until} minutes`;
  if (minutes_until >= 60) {
    const hrs = Math.floor(minutes_until / 60);
    const mins = minutes_until % 60;
    countdownDisplay = mins > 0 ? `Starts in ${hrs}h ${mins}m` : `Starts in ${hrs} hour${hrs > 1 ? 's' : ''}`;
  } else if (minutes_until === 1) {
    countdownDisplay = 'Starts in 1 minute';
  } else if (minutes_until <= 0) {
    countdownDisplay = 'Starting now';
  }

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl flex flex-col justify-between h-full min-h-[220px] relative overflow-hidden transition hover:border-[var(--border-hover)]">
      {/* Left accent color bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1.5"
        style={{ backgroundColor: barColor }}
      />

      <div>
        {/* Top meta: label + countdown pill */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: barColor }}
            />
            NEXT UP
          </span>

          <span
            className={`text-xs font-bold px-2.5 py-1 rounded-full border shadow-sm ${typeBadgeColor}`}
          >
            ⏱️ {countdownDisplay}
          </span>
        </div>

        {/* Title */}
        <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text-primary)] tracking-tight leading-snug">
          {block.title}
        </h2>

        {/* Start / End Time & Location */}
        <div className="mt-3 flex flex-wrap items-center gap-y-1 gap-x-3 text-xs sm:text-sm text-[var(--text-secondary)]">
          <span className="font-semibold text-[var(--text-primary)] bg-[var(--bg-secondary)] px-2 py-0.5 rounded border border-[var(--border-color)] font-mono">
            {block.start_time}{block.end_time ? ` – ${block.end_time}` : ''}
          </span>
          {block.location && (
            <span className="flex items-center gap-1 text-[var(--text-muted)]">
              <span>📍</span>
              <span className="truncate max-w-[160px]">{block.location}</span>
            </span>
          )}
        </div>
      </div>

      {/* Footer summary label + Open calendar button */}
      <div className="pt-4 mt-4 border-t border-[var(--border-color)] flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)] capitalize flex items-center gap-1.5">
          {isStudy && <span>📖</span>}
          <span className="capitalize font-medium">{block.type}</span>
          <span className="text-[var(--text-muted)] font-mono">({label})</span>
        </span>

        <Link
          href="/calendar"
          className="text-xs font-bold text-indigo-500 hover:text-indigo-400 transition flex items-center gap-1 cursor-pointer"
        >
          <span>Open calendar</span>
          <span>→</span>
        </Link>
      </div>
    </div>
  );
}
