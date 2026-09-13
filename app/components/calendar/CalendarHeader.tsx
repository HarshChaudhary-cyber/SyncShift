'use client';

import React from 'react';
import { addDays, format, parseISO } from 'date-fns';
import { useCalendar, CalendarViewMode } from '@/context/CalendarContext';

interface CalendarHeaderProps {
  onAddClass: () => void;
  onAddShift: () => void;
  onImport: () => void;
}

export default function CalendarHeader({
  onAddClass,
  onAddShift,
  onImport,
}: CalendarHeaderProps) {
  const {
    weekStart,
    goToPrevWeek,
    goToNextWeek,
    goToCurrentWeek,
    refreshWeek,
    loading,
    viewMode,
    setViewMode,
  } = useCalendar();

  // Calculate the formatted week date range: e.g. "Sep 7 – Sep 13, 2026"
  const startObj = parseISO(weekStart);
  const endDaysCount = viewMode === '5day' ? 4 : 6;
  const endObj = addDays(startObj, endDaysCount);

  const formattedDateRange = `${format(startObj, 'MMMM d')} – ${format(
    endObj,
    startObj.getMonth() === endObj.getMonth() ? 'd, yyyy' : 'MMMM d, yyyy'
  )}`;

  return (
    <div className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 sm:p-4 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-3">
      {/* LEFT: Calendar Title & Current Date Range */}
      <div className="flex flex-col gap-0.5">
        <div className="flex flex-wrap items-baseline gap-2 sm:gap-3">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <span>My Schedule</span>
          </h1>
          <span className="text-sm sm:text-base font-semibold text-[var(--text-secondary)]">
            {formattedDateRange}
          </span>
        </div>
        <p className="text-xs text-indigo-400 font-medium">
          See your classes, work, and personal time together.
        </p>
      </div>

      {/* CENTER: Navigation Steppers (< Today >) */}
      <div className="flex items-center gap-2 self-start lg:self-auto">
        <div className="flex items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-0.5 text-xs shadow-2xs">
          <button
            type="button"
            onClick={goToPrevWeek}
            title="Previous week"
            aria-label="Previous week"
            className="px-2.5 py-1.5 hover:bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded font-medium transition cursor-pointer"
          >
            ◀
          </button>
          <button
            type="button"
            onClick={goToCurrentWeek}
            title="Jump to current week"
            aria-label="Jump to current week"
            className="px-3 py-1.5 hover:bg-[var(--bg-card)] text-[var(--text-primary)] font-bold rounded transition cursor-pointer border-x border-[var(--border-color)]/60"
          >
            Today
          </button>
          <button
            type="button"
            onClick={goToNextWeek}
            title="Next week"
            aria-label="Next week"
            className="px-2.5 py-1.5 hover:bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded font-medium transition cursor-pointer"
          >
            ▶
          </button>
        </div>

        {/* View Mode Switcher: 5 Days vs 7 Days */}
        <div className="flex items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-0.5 text-xs shadow-2xs">
          <button
            type="button"
            onClick={() => setViewMode('5day')}
            className={`px-2.5 py-1.5 rounded font-medium transition cursor-pointer ${
              viewMode === '5day'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            5 Days
          </button>
          <button
            type="button"
            onClick={() => setViewMode('7day')}
            className={`px-2.5 py-1.5 rounded font-medium transition cursor-pointer ${
              viewMode === '7day'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            7 Days
          </button>
        </div>

        {/* Refresh button */}
        <button
          type="button"
          onClick={() => refreshWeek()}
          title="Refresh schedule"
          aria-label="Refresh schedule"
          className="p-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer shadow-2xs flex items-center justify-center"
        >
          <span className={`inline-block ${loading ? 'animate-spin' : ''}`}>↻</span>
        </button>
      </div>

      {/* RIGHT: Actions (+ Add Class, + Add Shift, Import) */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onImport}
          className="px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer shadow-2xs flex items-center gap-1.5"
        >
          <span>📁</span>
          <span>Import Timetable</span>
        </button>

        <button
          type="button"
          onClick={onAddClass}
          className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer shadow-xs flex items-center gap-1"
        >
          <span>+</span>
          <span>Add Class</span>
        </button>

        <button
          type="button"
          onClick={onAddShift}
          className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer shadow-xs flex items-center gap-1"
        >
          <span>+</span>
          <span>Add Shift</span>
        </button>
      </div>
    </div>
  );
}
