'use client';

import React from 'react';

interface QuickActionsProps {
  onAddClass: () => void;
  onAddShift: () => void;
  onImport: () => void;
  onAddStudyTask?: () => void;
}

export default function QuickActions({
  onAddClass,
  onAddShift,
  onImport,
  onAddStudyTask,
}: QuickActionsProps) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 sm:p-5 shadow-xl flex flex-wrap items-center justify-between gap-3">
      <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
        ⚡ Quick Actions
      </span>

      <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
        <button
          onClick={onAddClass}
          className="flex-1 sm:flex-none px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs sm:text-sm font-semibold transition shadow-md shadow-blue-950/40 flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <span>+</span>
          <span>Add Class</span>
        </button>

        <button
          onClick={onAddShift}
          className="flex-1 sm:flex-none px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs sm:text-sm font-semibold transition shadow-md shadow-emerald-950/40 flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <span>+</span>
          <span>Add Shift</span>
        </button>

        {onAddStudyTask && (
          <button
            onClick={onAddStudyTask}
            className="flex-1 sm:flex-none px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs sm:text-sm font-semibold transition shadow-md shadow-purple-950/40 flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <span>📖</span>
            <span>＋ Study Task</span>
          </button>
        )}

        <button
          onClick={onImport}
          className="flex-1 sm:flex-none px-4 py-2.5 bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-xl text-xs sm:text-sm font-semibold transition shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <span>📁</span>
          <span>Import Timetable</span>
        </button>
      </div>
    </div>
  );
}
