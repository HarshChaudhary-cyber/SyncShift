'use client';

import React from 'react';

interface TimeGutterProps {
  startHour: number;
  endHour: number;
  hourHeight: number;
}

export default function TimeGutter({
  startHour,
  endHour,
  hourHeight,
}: TimeGutterProps) {
  const totalHours = endHour - startHour;

  return (
    <div className="w-14 sm:w-16 shrink-0 border-r border-[var(--border-color)] bg-[var(--bg-card)]/95 sticky left-0 z-20 backdrop-blur-sm select-none">
      {/* Spacer matching DayHeader height (approx 68px) */}
      <div className="h-[69px] border-b border-[var(--border-color)] flex items-center justify-center text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider">
        Time
      </div>

      {/* Hourly labels */}
      <div style={{ height: `${totalHours * hourHeight}px` }} className="relative">
        {Array.from({ length: totalHours }).map((_, idx) => {
          const hour = startHour + idx;
          const displayHour =
            hour === 0
              ? '12 AM'
              : hour === 12
              ? '12 PM'
              : hour > 12
              ? `${hour - 12} PM`
              : `${hour} AM`;

          return (
            <div
              key={hour}
              style={{ top: `${idx * hourHeight}px` }}
              className="absolute left-0 right-0 pr-2 -translate-y-2 text-right font-mono text-[10px] sm:text-[11px] text-[var(--text-muted)] leading-none"
            >
              <span>{displayHour}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
