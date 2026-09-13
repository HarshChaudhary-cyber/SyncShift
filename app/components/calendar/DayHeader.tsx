'use client';

import React from 'react';
import { BlockOut } from '@/lib/api';

interface DayHeaderProps {
  dayName: string;
  dateStr: string;
  dayNumber: string;
  isToday: boolean;
  dayBlocks: BlockOut[];
}

export default function DayHeader({
  dayName,
  dateStr,
  dayNumber,
  isToday,
  dayBlocks,
}: DayHeaderProps) {
  // Calculate total scheduled hours for this day
  const totalMinutes = dayBlocks.reduce((acc, b) => {
    const sParts = b.start_time.split(':');
    const eParts = b.end_time.split(':');
    const s = parseInt(sParts[0], 10) * 60 + parseInt(sParts[1], 10);
    const e = parseInt(eParts[0], 10) * 60 + parseInt(eParts[1], 10);
    const dur = Math.max(0, e - s);
    return acc + dur;
  }, 0);

  const totalHours = (totalMinutes / 60).toFixed(1);
  const hasWorkload = totalMinutes > 0;

  // Workload intensity indicator
  const workloadColor =
    totalMinutes >= 7 * 60
      ? 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/30'
      : totalMinutes >= 4 * 60
      ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 border-indigo-500/30'
      : 'text-[var(--text-muted)] bg-[var(--bg-secondary)] border-[var(--border-color)]';

  return (
    <div
      className={`py-2 px-1 sm:px-2 text-center border-b border-[var(--border-color)] sticky top-0 z-20 backdrop-blur-md transition-colors ${
        isToday
          ? 'bg-indigo-500/5 dark:bg-indigo-950/20'
          : 'bg-[var(--bg-card)]/95'
      }`}
    >
      {/* Day Name (MON, TUE...) */}
      <p
        className={`text-[11px] sm:text-xs uppercase tracking-wider font-bold ${
          isToday ? 'text-indigo-600 dark:text-indigo-400' : 'text-[var(--text-secondary)]'
        }`}
      >
        {dayName}
      </p>

      {/* Date Number with Today Circle/Pill */}
      <div className="flex items-center justify-center gap-1.5 my-0.5">
        <span
          className={`inline-flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 text-sm sm:text-base font-bold rounded-full transition ${
            isToday
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30 ring-2 ring-indigo-400/40'
              : 'text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          {dayNumber}
        </span>
        {isToday && (
          <span className="hidden sm:inline-block text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-indigo-600/15 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">
            TODAY
          </span>
        )}
      </div>

      {/* Busy-Day Workload Indicator */}
      <div className="flex items-center justify-center">
        {hasWorkload ? (
          <span
            title={`${totalHours} hours scheduled on ${dayName}`}
            className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full border inline-flex items-center gap-1 leading-none ${workloadColor}`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                totalMinutes >= 7 * 60
                  ? 'bg-amber-500'
                  : totalMinutes >= 4 * 60
                  ? 'bg-indigo-500'
                  : 'bg-neutral-400'
              }`}
            />
            <span>{totalHours}h</span>
          </span>
        ) : (
          <span className="text-[10px] text-[var(--text-muted)] font-mono leading-none opacity-60">
            0h
          </span>
        )}
      </div>
    </div>
  );
}
