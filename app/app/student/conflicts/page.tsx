'use client';

import React from 'react';
import Link from 'next/link';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import { api } from '@/lib/api';
import { showErrorToast, showSuccessToast } from '@/lib/toast';

function ConflictsContent() {
  const { conflicts, blocks, loading, refreshWeek } = useCalendar();

  const handleReplanStudy = async (taskId: number) => {
    try {
      const res = await api.replanTask(taskId);
      if (res.suggested && res.suggested.length > 0) {
        await api.confirmTaskPlan(taskId, { approved_blocks: res.suggested });
        showSuccessToast('Study session moved to an open slot!');
        await refreshWeek();
      } else {
        showErrorToast('No free slots available before deadline.');
      }
    } catch (err: unknown) {
      showErrorToast((err as Error).message || 'Failed to replan study block');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚠️</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Schedule Conflicts
            </h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Real-time overlap detection between university lectures, work shifts, and study sessions.
          </p>
        </div>
        <Link
          href="/student/calendar"
          className="px-4 py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-xl text-xs font-semibold transition cursor-pointer self-start sm:self-auto"
        >
          📅 View in Calendar
        </Link>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Active Conflicts</p>
          <p
            className={`text-2xl font-black mt-1 ${
              conflicts.length > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {conflicts.length}
          </p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
            {conflicts.length === 0 ? 'All schedules are aligned' : 'Requires your attention'}
          </p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Conflict Engine Status</p>
          <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mt-2">Active & Monitoring</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
            Evaluates official timetable updates automatically
          </p>
        </div>
      </div>

      {/* Conflict List */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Detected Overlaps</h2>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Scanning schedule for overlaps…
          </div>
        ) : conflicts.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <span className="text-4xl">🎉</span>
            <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">No conflicts found!</p>
            <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
              Your university classes, employment shifts, and study sessions do not overlap.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map((conflict, index) => {
              const blockA = blocks.find((b) => b.id === conflict.block_a_id);
              const blockB = blocks.find((b) => b.id === conflict.block_b_id);

              const studyBlock =
                blockA?.type === 'study' ? blockA : blockB?.type === 'study' ? blockB : null;

              return (
                <div
                  key={index}
                  className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-base">🚨</span>
                      <p className="text-sm font-bold text-rose-800 dark:text-rose-300">
                        {blockA?.title || 'Event A'} ⚔️ {blockB?.title || 'Event B'}
                      </p>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {conflict.message || `${conflict.overlap_minutes} minutes overlap`}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-muted)] pt-1">
                      <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                        {blockA?.type?.toUpperCase() || 'EVENT'}
                      </span>
                      <span>clashes with</span>
                      <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                        {blockB?.type?.toUpperCase() || 'EVENT'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {studyBlock?.study_task_id && (
                      <button
                        onClick={() => handleReplanStudy(studyBlock.study_task_id!)}
                        className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer shadow-sm"
                      >
                        🔄 Auto-Replan Study
                      </button>
                    )}
                    <Link
                      href="/student/calendar"
                      className="px-3 py-1.5 bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-lg text-xs font-semibold transition"
                    >
                      Resolve in Calendar
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default function StudentConflictsPage() {
  return (
    <CalendarProvider>
      <ConflictsContent />
    </CalendarProvider>
  );
}
