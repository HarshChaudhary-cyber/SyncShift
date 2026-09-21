'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import { api, BlockOut } from '@/lib/api';
import { showErrorToast, showSuccessToast } from '@/lib/toast';
import TodayWidget from '@/components/calendar/TodayWidget';
import WeekView from '@/components/calendar/WeekView';
import CalendarHeader from '@/components/calendar/CalendarHeader';
import WeekSummaryBar from '@/components/calendar/WeekSummaryBar';
import CalendarSkeleton from '@/components/calendar/CalendarSkeleton';
import BlockModal, { SlotPreFill } from '@/components/calendar/BlockModal';
import ImportModal from '@/components/calendar/ImportModal';

function Spinner({ size = 20, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`animate-spin ${className}`}
      aria-hidden="true"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

function StudentCalendarContent() {
  const router = useRouter();
  const { status, onIdleReturn } = useAuthContext();
  const {
    blocks,
    conflicts,
    loading,
    lastUpdated,
    error,
    viewMode,
    goToPrevWeek,
    goToNextWeek,
    goToCurrentWeek,
    refreshWeek,
  } = useCalendar();

  const handleReplanStudy = async (taskId: number) => {
    try {
      const res = await api.replanTask(taskId);
      if (res.suggested && res.suggested.length > 0) {
        await api.confirmTaskPlan(taskId, { approved_blocks: res.suggested });
        showSuccessToast('Study slot automatically rescheduled into a free gap!');
        await refreshWeek();
      } else {
        showErrorToast('No free slots found before deadline. Try freeing up time.');
      }
    } catch (err: unknown) {
      showErrorToast((err as Error).message || 'Failed to replan study slot');
    }
  };

  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    initialBlock?: BlockOut | null;
    defaultType?: 'class' | 'shift' | 'study';
    preFill?: SlotPreFill | null;
  }>({ isOpen: false });

  const [importOpen, setImportOpen] = useState(false);

  const refreshWeekRef = useRef(refreshWeek);
  useEffect(() => { refreshWeekRef.current = refreshWeek; }, [refreshWeek]);

  useEffect(() => {
    onIdleReturn.current = () => {
      refreshWeekRef.current();
      showSuccessToast('Schedule refreshed after inactivity.');
    };
    return () => { onIdleReturn.current = null; };
  }, [onIdleReturn]);

  if (status === 'checking') {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
          <Spinner size={36} className="text-indigo-400" />
          <p className="text-sm">Loading your schedule…</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    router.replace('/login');
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Calendar Toolbar Header */}
      <CalendarHeader
        onAddClass={() => setModalState({ isOpen: true, defaultType: 'class' })}
        onAddShift={() => setModalState({ isOpen: true, defaultType: 'shift' })}
        onImport={() => setImportOpen(true)}
      />

      {/* Compact Weekly KPI Summary Bar */}
      <WeekSummaryBar />

      {/* Today's Timetable Preview Widget */}
      <TodayWidget
        refreshTrigger={lastUpdated}
        onBlockClick={(block) =>
          setModalState({
            isOpen: true,
            initialBlock: block,
            defaultType: block.type,
          })
        }
      />

      {/* Error banner */}
      {error && blocks.length > 0 && (
        <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-700 rounded-lg text-xs text-rose-700 dark:text-rose-300 flex justify-between items-center">
          <span>⚠ {error}</span>
          <button onClick={() => refreshWeek()} className="underline font-medium cursor-pointer ml-4">
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && blocks.length === 0 && (
        <CalendarSkeleton daysCount={viewMode === '5day' ? 5 : 7} />
      )}

      {/* Empty state */}
      {!loading && !error && blocks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center space-y-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-sm">
          <div className="text-6xl select-none">🗓️</div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Your schedule is empty.</h2>
            <p className="text-sm text-[var(--text-secondary)] max-w-sm">
              Import your timetable or create your first event.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-2.5 pt-2">
            <button
              onClick={() => setImportOpen(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition cursor-pointer shadow-xs"
            >
              📁 Import timetable
            </button>
            <button
              onClick={() => setModalState({ isOpen: true, defaultType: 'class' })}
              className="px-4 py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] text-xs font-semibold rounded-lg transition cursor-pointer shadow-2xs"
            >
              + Add event
            </button>
          </div>
        </div>
      )}

      {/* No conflicts positive state */}
      {!loading && !error && blocks.length > 0 && conflicts.length === 0 && (
        <div className="p-3.5 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-300 dark:border-emerald-500/30 rounded-xl text-xs text-emerald-800 dark:text-emerald-200 flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2.5 font-medium">
            <span className="text-emerald-600 dark:text-emerald-400 font-bold text-sm">✓</span>
            <div>
              <span className="font-bold">No conflicts this week</span>
              <span className="text-emerald-700 dark:text-emerald-300 ml-1.5 hidden sm:inline">
                · Your schedule looks good.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Conflict Alert Banner */}
      {conflicts.length > 0 && (
        <div className="p-3.5 bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-600/70 rounded-xl text-xs text-rose-800 dark:text-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">⚠️</span>
            <div>
              <span className="font-semibold text-rose-950 dark:text-rose-100 text-sm">
                {conflicts.length} Schedule Conflict{conflicts.length > 1 ? 's' : ''} Detected
              </span>
              <p className="text-rose-700 dark:text-rose-300 text-[11px] mt-0.5">
                {conflicts.map((c) => c.message || `${c.overlap_minutes}m overlap`).join(' · ')}
              </p>
            </div>
          </div>
          {(() => {
            const studyConflict = conflicts.find((c) => {
              const a = blocks.find((b) => b.id === c.block_a_id);
              const b = blocks.find((blk) => blk.id === c.block_b_id);
              return (a?.type === 'study' && a.study_task_id) || (b?.type === 'study' && b.study_task_id);
            });
            const studyTaskId = studyConflict
              ? blocks.find((b) => b.id === studyConflict.block_a_id && b.type === 'study')?.study_task_id ??
                blocks.find((b) => b.id === studyConflict.block_b_id && b.type === 'study')?.study_task_id
              : null;
            return studyTaskId ? (
              <button
                type="button"
                onClick={() => handleReplanStudy(studyTaskId)}
                className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-semibold text-xs transition flex items-center gap-1.5 shrink-0 shadow cursor-pointer self-start sm:self-auto"
                title="Automatically move study session into an open free gap"
              >
                <span>🔄 Find another study slot</span>
              </button>
            ) : null;
          })()}
        </div>
      )}

      {/* Week View grid */}
      {(blocks.length > 0 || loading) && !(!loading && error && blocks.length === 0) && (
        <WeekView
          onBlockClick={(block) =>
            setModalState({ isOpen: true, initialBlock: block, defaultType: block.type })
          }
          onSlotClick={(dayIndex, startTime, endTime) =>
            setModalState({
              isOpen: true,
              defaultType: 'class',
              preFill: { dayIndex, startTime, endTime },
            })
          }
          onReplanStudy={handleReplanStudy}
        />
      )}

      {/* Modals */}
      <BlockModal
        isOpen={modalState.isOpen}
        initialBlock={modalState.initialBlock}
        defaultType={modalState.defaultType}
        preFill={modalState.preFill}
        onClose={() => setModalState({ isOpen: false })}
      />

      <ImportModal
        isOpen={importOpen}
        onClose={() => setImportOpen(false)}
        onToast={(msg) => showSuccessToast(msg)}
      />
    </div>
  );
}

export default function StudentCalendarPage() {
  const router = useRouter();
  const { logout } = useAuthContext();

  return (
    <CalendarProvider
      onUnauthorized={() => {
        logout();
        router.replace('/login');
      }}
    >
      <StudentCalendarContent />
    </CalendarProvider>
  );
}
