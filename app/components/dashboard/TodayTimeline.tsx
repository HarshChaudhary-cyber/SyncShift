'use client';

import React from 'react';
import { DashboardBlock, DashboardToday } from '@/lib/api';

interface TodayTimelineProps {
  today: DashboardToday | null;
  currency?: string;
  loading?: boolean;
}

export default function TodayTimeline({
  today,
  currency = '₹',
  loading,
}: TodayTimelineProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-lg flex flex-col justify-between h-full min-h-[300px] animate-pulse">
        <div className="space-y-4">
          <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/4" />
          <div className="space-y-3">
            <div className="h-12 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-12 bg-[var(--bg-secondary)] rounded-xl" />
            <div className="h-12 bg-[var(--bg-secondary)] rounded-xl" />
          </div>
        </div>
        <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/2 mt-4" />
      </div>
    );
  }

  const blocks = today?.blocks || [];
  const conflicts = today?.conflicts || [];

  // Build sets for hard conflicts vs transition warnings
  const hardConflictBlockIds = new Set<number>();
  const transitionWarningBlockIds = new Set<number>();
  conflicts.forEach((c) => {
    if (c.severity === 'warning' || c.conflict_type === 'transition') {
      transitionWarningBlockIds.add(c.block_a_id);
      transitionWarningBlockIds.add(c.block_b_id);
    } else {
      hardConflictBlockIds.add(c.block_a_id);
      hardConflictBlockIds.add(c.block_b_id);
    }
  });

  // Calculate classes, shifts, and study sessions count
  let classCount = 0;
  let shiftCount = 0;
  let studyCount = 0;
  blocks.forEach((b) => {
    if (b.type === 'shift') shiftCount++;
    else if (b.type === 'class') classCount++;
    else if (b.type === 'study') studyCount++;
  });

  const shiftHours = today?.shift_hours || 0;
  const expectedEarnings = today?.expected_earnings || 0;

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col justify-between h-full min-h-[300px]">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>📅</span>
            <span>Today's Schedule</span>
          </h2>
          <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
            {today?.day_name || 'Today'}
          </span>
        </div>

        {/* Timeline rows or empty state */}
        {blocks.length === 0 ? (
          <div className="py-12 px-4 text-center">
            <div className="text-4xl mb-3">📅</div>
            <h3 className="text-base font-semibold text-[var(--text-primary)]">
              Your schedule is empty today
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-xs mx-auto">
              Import your timetable or create your first event to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
            {blocks.map((block) => {
              const isHardConflict = hardConflictBlockIds.has(block.id);
              const isTransitionWarning = !isHardConflict && transitionWarningBlockIds.has(block.id);
              const isShift = block.type === 'shift';
              const isStudy = block.type === 'study';
              const dotColor = block.color || (isStudy ? '#8B5CF6' : isShift ? '#10B981' : '#4F46E5');
              const blockKey = block.occurrence_date ? `${block.id}-${block.occurrence_date}` : block.id;

              return (
                <div
                  key={blockKey}
                  className={`relative flex items-center justify-between gap-3 p-3 rounded-xl border transition ${
                    block.is_now
                      ? 'bg-indigo-500/10 border-indigo-500 shadow-md ring-1 ring-indigo-500/40'
                      : isHardConflict
                      ? 'bg-rose-500/10 border-rose-500/50 text-[var(--conflict-text)] border-l-4 border-l-rose-500'
                      : isTransitionWarning
                      ? 'bg-amber-500/10 border-amber-500/40 text-amber-900 dark:text-amber-200 border-l-4 border-l-amber-500'
                      : 'bg-[var(--bg-secondary)] border-[var(--border-color)] hover:border-[var(--border-hover)]'
                  }`}
                >
                  {/* Left: Time & Color Dot & Title */}
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-mono text-xs font-bold text-[var(--text-secondary)] shrink-0 min-w-[42px]">
                      {block.start_time}
                    </span>

                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                      style={{ backgroundColor: dotColor }}
                    />

                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {isStudy && <span className="text-xs">📖</span>}
                        <span className="text-sm font-semibold text-[var(--text-primary)] truncate">
                          {block.title}
                        </span>
                        {isTransitionWarning && (
                          <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30 shrink-0">
                            ⚠ Short transition
                          </span>
                        )}
                        {block.is_now && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-extrabold px-1.5 py-0.5 rounded bg-indigo-500 text-white animate-pulse shadow-sm">
                            <span className="w-1.5 h-1.5 rounded-full bg-white" />
                            NOW
                          </span>
                        )}
                      </div>

                      {block.location && (
                        <p className="text-xs text-[var(--text-muted)] flex items-center gap-1 mt-0.5 truncate">
                          <span>📍</span>
                          <span>{block.location}</span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Right: End Time & Type pill */}
                  <div className="shrink-0 text-right">
                    <span className="text-xs font-mono text-[var(--text-muted)] block">
                      {block.end_time}
                    </span>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--text-muted)]">
                      {block.type}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer summary */}
      <div className="pt-4 mt-4 border-t border-[var(--border-color)] flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
        <div className="flex flex-wrap items-center gap-2">
          <span>{classCount} {classCount === 1 ? 'class' : 'classes'}</span>
          <span>·</span>
          <span>{shiftCount} {shiftCount === 1 ? 'shift' : 'shifts'} ({shiftHours}h)</span>
          {studyCount > 0 && (
            <>
              <span>·</span>
              <span className="text-purple-600 dark:text-purple-300 font-medium">📖 {studyCount} study {studyCount === 1 ? 'session' : 'sessions'}</span>
            </>
          )}
        </div>
        {expectedEarnings > 0 && (
          <div className="font-semibold text-emerald-600 dark:text-emerald-400" suppressHydrationWarning>
            {currency}{expectedEarnings.toLocaleString()} expected today
          </div>
        )}
      </div>
    </div>
  );
}
