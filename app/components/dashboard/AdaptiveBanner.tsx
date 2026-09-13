'use client';

import React from 'react';

interface AdaptiveBannerProps {
  adaptiveState?: 'new_user' | 'academic_only' | 'conflicts' | 'over_work_limit' | 'near_work_limit' | 'on_track' | string | null;
  onImportClick?: () => void;
  onAddShiftClick?: () => void;
}

export default function AdaptiveBanner({
  adaptiveState,
  onImportClick,
  onAddShiftClick,
}: AdaptiveBannerProps) {
  if (!adaptiveState || (adaptiveState !== 'new_user' && adaptiveState !== 'academic_only')) {
    return null;
  }

  if (adaptiveState === 'new_user') {
    return (
      <div className="bg-gradient-to-r from-indigo-500/15 via-purple-500/15 to-blue-500/15 border border-indigo-500/30 rounded-2xl p-6 shadow-xl mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-2xl">👋</span>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">
              Welcome to SyncShift
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-[var(--text-secondary)] max-w-xl leading-relaxed">
            Import your university timetable or add your first event to automatically detect schedule conflicts, track work-hour limits, and balance study sessions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          {onImportClick && (
            <button
              onClick={onImportClick}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-indigo-900/30 flex items-center gap-2 cursor-pointer"
            >
              <span>📥</span>
              <span>Import Timetable</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  if (adaptiveState === 'academic_only') {
    return (
      <div className="bg-gradient-to-r from-blue-500/15 via-emerald-500/15 to-teal-500/15 border border-blue-500/30 rounded-2xl p-6 shadow-xl mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 backdrop-blur-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎓</span>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">
              Your academic schedule is ready
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-[var(--text-secondary)] max-w-xl leading-relaxed">
            Add your part-time work shifts to activate real-time conflict detection and track student visa or contract work-hour limits.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {onAddShiftClick && (
            <button
              onClick={onAddShiftClick}
              className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-900/30 flex items-center gap-2 cursor-pointer"
            >
              <span>💼</span>
              <span>Add Work Shift</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}
