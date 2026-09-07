'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { TimeBlock } from './CalendarWeekView';
import type { ReviewItem, Section } from '@/lib/icsParser';

export interface ImportSummaryModalProps {
  open: boolean;
  onClose: () => void;
  onGoToCalendar: () => void;
  importedCount: number;
  conflicts: TimeBlock[];
  reviewItems: ReviewItem[];
  importedSections: Section[];
}

function fmt12h(timeStr: string): string {
  if (!timeStr) return '';
  const parts = timeStr.split(':');
  const h = parseInt(parts[0] ?? '0', 10) || 0;
  const m = parseInt(parts[1] ?? '0', 10) || 0;
  const period = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${String(m).padStart(2, '0')} ${period}`;
}

export const ImportSummaryModal: React.FC<ImportSummaryModalProps> = ({
  open,
  onClose,
  onGoToCalendar,
  importedCount,
  conflicts,
  reviewItems,
  importedSections,
}) => {
  if (!open) return null;

  const conflictCount = conflicts.length;
  const reviewCount = reviewItems.length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Backdrop blur */}
      <motion.div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        aria-hidden="true"
      />

      {/* Modal card */}
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label="Import timetable summary"
        className="relative w-full max-w-lg max-h-[85vh] flex flex-col rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-2xl shadow-black/40 overflow-hidden"
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.97 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-100 dark:border-zinc-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                Timetable Import Summary
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Processed university schedule file
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Close summary"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4 text-xs">
          {/* Main stat highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {/* Classes count */}
            <div className="p-3 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/60 dark:bg-blue-950/30">
              <div className="text-[11px] font-medium text-blue-700 dark:text-blue-300">
                Classes
              </div>
              <div className="text-lg font-bold text-blue-900 dark:text-blue-100 mt-0.5">
                {importedCount}
              </div>
              <div className="text-[10px] text-blue-600/80 dark:text-blue-400 mt-0.5">
                Imported successfully
              </div>
            </div>

            {/* Conflicts count */}
            <div
              className={`p-3 rounded-xl border ${
                conflictCount > 0
                  ? 'border-rose-200 dark:border-rose-900/70 bg-rose-50/70 dark:bg-rose-950/30'
                  : 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/60 dark:bg-emerald-950/30'
              }`}
            >
              <div
                className={`text-[11px] font-medium ${
                  conflictCount > 0
                    ? 'text-rose-700 dark:text-rose-300'
                    : 'text-emerald-700 dark:text-emerald-300'
                }`}
              >
                Conflicts
              </div>
              <div
                className={`text-lg font-bold mt-0.5 ${
                  conflictCount > 0
                    ? 'text-rose-900 dark:text-rose-100'
                    : 'text-emerald-900 dark:text-emerald-100'
                }`}
              >
                {conflictCount}
              </div>
              <div
                className={`text-[10px] mt-0.5 ${
                  conflictCount > 0
                    ? 'text-rose-600/80 dark:text-rose-400'
                    : 'text-emerald-600/80 dark:text-emerald-400'
                }`}
              >
                {conflictCount > 0 ? 'Overlaps with shifts' : 'No clashes found'}
              </div>
            </div>

            {/* Review items count */}
            <div
              className={`p-3 rounded-xl col-span-2 sm:col-span-1 border ${
                reviewCount > 0
                  ? 'border-amber-200 dark:border-amber-900/60 bg-amber-50/60 dark:bg-amber-950/30'
                  : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-900/40'
              }`}
            >
              <div
                className={`text-[11px] font-medium ${
                  reviewCount > 0
                    ? 'text-amber-700 dark:text-amber-300'
                    : 'text-zinc-600 dark:text-zinc-400'
                }`}
              >
                Manual Review
              </div>
              <div
                className={`text-lg font-bold mt-0.5 ${
                  reviewCount > 0
                    ? 'text-amber-900 dark:text-amber-100'
                    : 'text-zinc-900 dark:text-zinc-100'
                }`}
              >
                {reviewCount}
              </div>
              <div
                className={`text-[10px] mt-0.5 ${
                  reviewCount > 0
                    ? 'text-amber-600/80 dark:text-amber-400'
                    : 'text-zinc-500'
                }`}
              >
                {reviewCount > 0 ? 'Needs manual check' : 'Clean mapping'}
              </div>
            </div>
          </div>

          {/* Primary Result Banner */}
          <div
            className={`p-3.5 rounded-xl border flex items-center gap-3 ${
              conflictCount > 0
                ? 'border-rose-300 dark:border-rose-900/80 bg-rose-50/50 dark:bg-rose-950/20 text-rose-900 dark:text-rose-200'
                : 'border-emerald-300 dark:border-emerald-900/80 bg-emerald-50/50 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-200'
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                conflictCount > 0
                  ? 'bg-rose-600 text-white'
                  : 'bg-emerald-600 text-white'
              }`}
            >
              {conflictCount > 0 ? '!' : '✓'}
            </div>
            <div className="flex-1">
              <span className="font-semibold text-sm">
                Imported {importedCount} {importedCount === 1 ? 'class' : 'classes'}, found{' '}
                {conflictCount} {conflictCount === 1 ? 'conflict' : 'conflicts'}
              </span>
              <p className="text-[11px] opacity-90 mt-0.5">
                {conflictCount > 0
                  ? 'There is a scheduling collision between your university classes and work shifts.'
                  : 'All classes fit cleanly around your existing shifts.'}
              </p>
            </div>
          </div>

          {/* Conflict List (if any) */}
          {conflictCount > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-zinc-700 dark:text-zinc-300 font-semibold">
                <span className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  Detected Conflicts ({conflictCount})
                </span>
                <span className="text-[11px] text-zinc-400 font-normal">
                  Class ↔ Shift overlap
                </span>
              </div>
              <div className="space-y-1.5">
                {conflicts.map((c) => {
                  const isWarning = c.conflictMetadata?.severity === 'warning';
                  return (
                    <div
                      key={c.id}
                      className={`p-3 rounded-xl border flex items-start justify-between gap-3 ${
                        isWarning
                          ? 'border-amber-200 dark:border-amber-900/70 bg-amber-50/40 dark:bg-amber-950/30'
                          : 'border-rose-200 dark:border-rose-900/70 bg-rose-50/40 dark:bg-rose-950/30'
                      }`}
                    >
                      <div>
                        <div className={`font-semibold ${isWarning ? 'text-amber-950 dark:text-amber-100' : 'text-rose-950 dark:text-rose-100'}`}>
                          {c.label}
                        </div>
                        <div className={`text-[11px] mt-0.5 ${isWarning ? 'text-amber-700 dark:text-amber-300' : 'text-rose-700 dark:text-rose-300'}`}>
                          {c.day} · {fmt12h(c.startTime)} – {fmt12h(c.endTime)}
                          {c.subLabel ? ` (${c.subLabel})` : ''}
                        </div>
                        {c.conflictMetadata?.actionableSuggestion && (
                          <div className={`text-[10px] mt-1 font-medium ${isWarning ? 'text-amber-800 dark:text-amber-200' : 'text-rose-800 dark:text-rose-200'}`}>
                            ⚡ {c.conflictMetadata.actionableSuggestion}
                          </div>
                        )}
                      </div>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded shrink-0 ${
                          isWarning ? 'bg-amber-600 text-white' : 'bg-rose-600 text-white'
                        }`}
                      >
                        {isWarning ? 'Warning' : 'Hard Conflict'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Manual Review Items (if any) */}
          {reviewCount > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-amber-700 dark:text-amber-400 font-semibold">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  {reviewCount} event{reviewCount === 1 ? '' : 's'} need manual review
                </span>
                <span className="text-[11px] text-zinc-400 font-normal">
                  Flagged, not dropped
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                These events could not be placed onto the weekly timetable automatically (e.g. all-day event, missing lecture hours). You can add them manually with &quot;+ Add Class&quot;.
              </p>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {reviewItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-2.5 rounded-lg border border-amber-200/80 dark:border-amber-900/50 bg-amber-50/30 dark:bg-amber-950/20 text-xs"
                  >
                    <div className="font-medium text-amber-950 dark:text-amber-200">
                      {item.summary}
                    </div>
                    <div className="text-[11px] text-amber-700 dark:text-amber-400 mt-0.5">
                      {item.reason}
                      {item.rawDateOrDetails ? ` (${item.rawDateOrDetails})` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Imported Classes list */}
          {importedCount > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-zinc-700 dark:text-zinc-300 font-semibold">
                <span>Imported Classes ({importedCount})</span>
                <span className="text-[10px] text-zinc-400 font-normal">
                  Saved to calendar
                </span>
              </div>
              <div className="max-h-44 overflow-y-auto space-y-1.5 pr-1">
                {importedSections.map((sec) => (
                  <div
                    key={sec.id}
                    className="p-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {sec.courseCode ? `${sec.courseCode}: ` : ''}
                        {sec.courseName}
                      </div>
                      <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                        {sec.day} · {fmt12h(sec.startTime)} – {fmt12h(sec.endTime)}
                        {sec.room ? ` · ${sec.room}` : ''}
                      </div>
                    </div>
                    {sec.repeatsWeekly && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium shrink-0">
                        Weekly
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Shift Protection Reassurance */}
          <div className="p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500 dark:text-zinc-400 flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span>
              Your manually added shifts are protected and were not touched by this import.
            </span>
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-2.5 px-6 py-3.5 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-lg hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={onGoToCalendar}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-all active:scale-[0.98]"
          >
            View in Calendar
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </motion.div>
    </div>
  );
};
export default ImportSummaryModal;
