'use client';

import React from 'react';
import { BlockOut, ConflictItem } from '@/lib/api';

interface EventHoverCardProps {
  block: BlockOut;
  activeConflict?: ConflictItem | null;
  conflictingBlock?: BlockOut | null;
  durationMinutes: number;
}

export default function EventHoverCard({
  block,
  activeConflict,
  conflictingBlock,
  durationMinutes,
}: EventHoverCardProps) {
  const hours = Math.floor(durationMinutes / 60);
  const mins = durationMinutes % 60;
  const durationText =
    hours > 0 ? `${hours}h${mins > 0 ? ` ${mins}m` : ''}` : `${mins}m`;

  const typeColor =
    block.type === 'shift'
      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
      : block.type === 'study'
      ? 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30'
      : 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30';

  const typeLabel =
    block.type === 'shift'
      ? 'Work Shift'
      : block.type === 'study'
      ? 'Study Session'
      : 'Class Timetable';

  const estEarnings =
    block.type === 'shift' && block.hourly_wage
      ? (block.hourly_wage * (durationMinutes / 60)).toFixed(2)
      : null;

  return (
    <div
      role="tooltip"
      className="w-64 p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl backdrop-blur-md text-left z-50 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-150 pointer-events-none"
    >
      {/* Header: Title + Type Badge */}
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-semibold text-xs text-[var(--text-primary)] leading-snug line-clamp-2">
          {block.title}
        </h4>
        <span
          className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${typeColor}`}
        >
          {typeLabel}
        </span>
      </div>

      {/* Time & Duration */}
      <div className="mt-2 flex items-center gap-1.5 text-xs text-[var(--text-secondary)] font-mono">
        <span>🕒</span>
        <span>
          {block.start_time.slice(0, 5)} – {block.end_time.slice(0, 5)}
        </span>
        <span className="text-[var(--text-muted)] font-sans">({durationText})</span>
      </div>

      {/* Location */}
      {block.location && (
        <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-muted)] truncate">
          <span>📍</span>
          <span className="truncate">{block.location}</span>
        </div>
      )}

      {/* Earnings if Shift */}
      {estEarnings && (
        <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          <span>💵</span>
          <span>
            ${estEarnings} (${block.hourly_wage?.toFixed(2)}/hr)
          </span>
        </div>
      )}

      {/* Conflict Status Section */}
      <div className="mt-2.5 pt-2 border-t border-[var(--border-color)] text-[11px]">
        {activeConflict ? (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-rose-500 font-semibold">
              <span className="flex items-center gap-1">
                <span>⚠️</span> Schedule Conflict
              </span>
              <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                {activeConflict.severity || 'Overlap'}
              </span>
            </div>
            <p className="text-rose-400 dark:text-rose-300 text-[11px] leading-tight">
              Overlaps {activeConflict.overlap_minutes}m
              {conflictingBlock ? ` with "${conflictingBlock.title}"` : ''}
            </p>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
            <span>✓</span>
            <span>No scheduling conflict</span>
          </div>
        )}
      </div>
    </div>
  );
}
