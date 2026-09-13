'use client';

import React from 'react';

export default function CalendarSkeleton({ daysCount = 7 }: { daysCount?: number }) {
  return (
    <div className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-md animate-pulse">
      {/* Legend placeholder */}
      <div className="px-4 py-3 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center justify-between">
        <div className="h-4 w-48 bg-[var(--border-color)] rounded" />
        <div className="h-4 w-32 bg-[var(--border-color)] rounded" />
      </div>

      {/* Grid */}
      <div className="flex divide-x divide-[var(--border-color)]">
        {/* Time gutter */}
        <div className="w-14 sm:w-16 shrink-0 bg-[var(--bg-card)] p-2 space-y-8">
          <div className="h-8 w-8 bg-[var(--border-color)] rounded mx-auto" />
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-3 w-8 bg-[var(--border-color)]/60 rounded ml-auto" />
          ))}
        </div>

        {/* Day columns */}
        {Array.from({ length: daysCount }).map((_, i) => (
          <div key={i} className="flex-1 min-w-[125px] p-2 space-y-3">
            {/* Header placeholder */}
            <div className="h-12 bg-[var(--border-color)]/50 rounded-lg mx-auto mb-4" />
            {/* Some placeholder blocks */}
            {i % 2 === 0 ? (
              <div className="h-20 bg-blue-500/10 border border-blue-500/20 rounded-lg mt-8" />
            ) : i % 3 === 0 ? (
              <div className="h-28 bg-emerald-500/10 border border-emerald-500/20 rounded-lg mt-16" />
            ) : (
              <div className="h-16 bg-purple-500/10 border border-purple-500/20 rounded-lg mt-24" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
