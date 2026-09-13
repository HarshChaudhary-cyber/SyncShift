'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { useAuthContext } from '@/context/AuthContext';
import { useThemeContext } from '@/context/ThemeContext';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import { api, BlockOut } from '@/lib/api';
import { showErrorToast, showSuccessToast } from '@/lib/toast';
import ProtectedRoute from '@/components/ProtectedRoute';
import SummaryCard from '@/components/calendar/SummaryCard';
import TodayWidget from '@/components/calendar/TodayWidget';

import WeekView from '@/components/calendar/WeekView';
import CalendarHeader from '@/components/calendar/CalendarHeader';
import WeekSummaryBar from '@/components/calendar/WeekSummaryBar';
import CalendarSkeleton from '@/components/calendar/CalendarSkeleton';
import BlockModal, { SlotPreFill } from '@/components/calendar/BlockModal';
import ImportModal from '@/components/calendar/ImportModal';

// ─── Spinner ──────────────────────────────────────────────────────────────────

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

// ─── Inner calendar content (inside CalendarProvider) ─────────────────────────

function CalendarContent() {
  const router = useRouter();
  const { status, user, logout, onIdleReturn } = useAuthContext();
  const { resolvedTheme, toggleTheme } = useThemeContext();
  const {
    weekStart,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Wire idle-return callback: when useAuth detects the user returned after
  // 30+ min of inactivity, refreshWeek() is called automatically.
  // We use a stable ref so the effect only runs once.
  const refreshWeekRef = useRef(refreshWeek);
  useEffect(() => { refreshWeekRef.current = refreshWeek; }, [refreshWeek]);

  useEffect(() => {
    onIdleReturn.current = () => {
      refreshWeekRef.current();
      showSuccessToast('Schedule refreshed after inactivity.');
    };
    return () => { onIdleReturn.current = null; };
  }, [onIdleReturn]);

  // ── Auth guard ──────────────────────────────────────────────────────────
  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
          <Spinner size={36} className="text-indigo-400" />
          <p className="text-sm">Loading your schedule…</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    // Redirect is handled by the parent wrapper via onUnauthorized, but also
    // guard here in case the context status changes during navigation.
    router.replace('/login');
    return null;
  }

  // ── Error state ─────────────────────────────────────────────────────────
  if (!loading && error && blocks.length === 0) {
    const isNetworkError = !error.toLowerCase().includes('401');
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center px-4">
        <div className="max-w-sm w-full text-center space-y-4">
          <div className="text-5xl">📡</div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            {isNetworkError
              ? "Unable to load your schedule."
              : 'Session expired'}
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">
            {isNetworkError
              ? 'Check your internet connection and try again.'
              : 'Your session has expired. Please sign in again.'}
          </p>
          <div className="flex justify-center gap-3">
            {isNetworkError ? (
              <button
                onClick={() => refreshWeek()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition cursor-pointer shadow-sm"
              >
                Try again
              </button>
            ) : (
              <button
                onClick={() => { logout(); router.replace('/login'); }}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition cursor-pointer"
              >
                Sign In Again
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── Main calendar UI ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col transition-colors duration-200">

      {/* ── Header ── */}
      <header className="border-b border-[var(--border-color)] bg-[var(--navbar-bg)] sticky top-0 z-30 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between gap-2">

          {/* Left: wordmark + nav tabs + week badge + last-updated */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <Link href="/dashboard" className="flex items-center gap-1.5 sm:gap-2 text-[var(--text-primary)] font-bold text-base sm:text-lg hover:opacity-80">
              <span className="text-lg sm:text-xl text-indigo-500">⚡</span>
              <span>SyncShift</span>
            </Link>

            {/* Nav links */}
            <div className="hidden md:flex items-center gap-1 bg-[var(--bg-secondary)] p-0.5 rounded-lg border border-[var(--border-color)] text-xs">
              <Link
                href="/dashboard"
                className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition"
              >
                🏠 Dashboard
              </Link>
              <Link
                href="/planner"
                className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition"
              >
                📖 Planner
              </Link>
              <span className="px-2.5 py-1 rounded bg-indigo-600 text-white font-semibold shadow-sm">
                📅 My Schedule
              </span>
            </div>

            <span className="text-[11px] sm:text-xs px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-500 font-mono">
              <span className="hidden sm:inline">Week of </span>{weekStart}
            </span>
            {lastUpdated && (
              <span className="hidden lg:inline text-[11px] text-[var(--text-muted)]">
                Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
              </span>
            )}
          </div>

          {/* Mobile quick controls (steppers + theme + hamburger) */}
          <div className="flex items-center gap-1.5 sm:hidden">
            {/* Quick theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
              aria-label="Toggle theme"
              title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              <span className="text-xs select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
            </button>

            {/* Compact steppers */}
            <div className="flex items-center bg-[var(--bg-card)] rounded-lg p-0.5 border border-[var(--border-color)] text-xs">
              <button onClick={goToPrevWeek} title="Previous week" className="px-2 py-1 hover:bg-[var(--bg-secondary)] rounded transition cursor-pointer">
                ◀
              </button>
              <button onClick={goToCurrentWeek} title="Go to current week" className="px-2 py-1 hover:bg-[var(--bg-secondary)] rounded font-medium transition cursor-pointer text-[11px]">
                Today
              </button>
              <button onClick={goToNextWeek} title="Next week" className="px-2 py-1 hover:bg-[var(--bg-secondary)] rounded transition cursor-pointer">
                ▶
              </button>
            </div>

            {/* Mobile menu toggle */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="p-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
              aria-label="Toggle calendar menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>

          {/* Desktop Right: user email + full controls */}
          <div className="hidden sm:flex flex-wrap items-center gap-2">
            {/* Quick theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer shadow-xs"
              aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              title={resolvedTheme === 'dark' ? 'Switch to light mode (☀️)' : 'Switch to dark mode (🌙)'}
            >
              <span className="text-xs select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
            </button>

            {/* User email pill */}
            {user && (
              <span className="hidden md:inline text-xs text-[var(--text-muted)] border border-[var(--border-color)] rounded-full px-3 py-1">
                {user.email}
              </span>
            )}

            {/* Week steppers */}
            <div className="flex items-center bg-[var(--bg-card)] rounded-lg p-0.5 border border-[var(--border-color)] text-xs">
              <button onClick={goToPrevWeek} title="Previous week" className="px-2.5 py-1 hover:bg-[var(--bg-secondary)] rounded transition cursor-pointer">
                ◀
              </button>
              <button onClick={goToCurrentWeek} title="Go to current week" className="px-3 py-1 hover:bg-[var(--bg-secondary)] rounded font-medium transition cursor-pointer">
                Today
              </button>
              <button onClick={goToNextWeek} title="Next week" className="px-2.5 py-1 hover:bg-[var(--bg-secondary)] rounded transition cursor-pointer">
                ▶
              </button>
            </div>

            {/* Manual refresh */}
            <button
              onClick={() => {
                refreshWeek();
                showSuccessToast('Schedule refreshed.');
              }}
              title="Refresh schedule"
              className="px-2.5 py-1.5 bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer shadow-xs"
            >
              ↻ Refresh
            </button>

            {/* Import timetable */}
            <button
              onClick={() => setImportOpen(true)}
              className="px-3 py-1.5 bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer shadow-xs"
            >
              📁 Import Timetable
            </button>

            {/* Add class */}
            <button
              onClick={() => setModalState({ isOpen: true, defaultType: 'class' })}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-medium text-white transition shadow-sm cursor-pointer"
            >
              + Add Class
            </button>

            {/* Add shift */}
            <button
              onClick={() => setModalState({ isOpen: true, defaultType: 'shift' })}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-medium text-white transition shadow-sm cursor-pointer"
            >
              + Add Shift
            </button>

            {/* Logout */}
            <button
              onClick={() => { logout(); router.push('/login'); }}
              title="Sign out"
              className="px-2.5 py-1.5 bg-neutral-800 hover:bg-red-900/60 border border-neutral-700 hover:border-red-700/60 rounded-lg text-xs text-neutral-400 hover:text-red-300 transition cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Mobile dropdown drawer */}
        {mobileMenuOpen && (
          <div className="border-t border-neutral-800 bg-neutral-900 px-4 py-3 sm:hidden flex flex-col gap-2.5 shadow-xl animate-in fade-in duration-150">
            {user && (
              <div className="text-xs text-neutral-400 px-2 py-1 border-b border-neutral-800 pb-2">
                Signed in as: <span className="text-neutral-200 font-mono">{user.email}</span>
              </div>
            )}
            <Link
              href="/dashboard"
              className="w-full py-2 px-3 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg text-xs font-semibold text-neutral-200 transition text-center"
            >
              🏠 Go to Dashboard
            </Link>
            <Link
              href="/planner"
              className="w-full py-2 px-3 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg text-xs font-semibold text-neutral-200 transition text-center"
            >
              📖 Go to Planner
            </Link>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setModalState({ isOpen: true, defaultType: 'class' });
                }}
                className="w-full py-2.5 px-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition cursor-pointer text-center"
              >
                + Add Class
              </button>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setModalState({ isOpen: true, defaultType: 'shift' });
                }}
                className="w-full py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-semibold text-white transition cursor-pointer text-center"
              >
                + Add Shift
              </button>
            </div>
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                setImportOpen(true);
              }}
              className="w-full py-2 px-3 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg text-xs font-medium text-neutral-200 transition cursor-pointer flex items-center justify-center gap-2"
            >
              <span>📁</span>
              <span>Import Timetable</span>
            </button>
            <div className="flex items-center justify-between pt-1 border-t border-neutral-800/80 text-xs">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  refreshWeek();
                  showSuccessToast('Schedule refreshed.');
                }}
                className="text-neutral-400 hover:text-white py-1.5 transition cursor-pointer"
              >
                ↻ Refresh
              </button>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  logout();
                  router.push('/login');
                }}
                className="text-rose-400 hover:text-rose-300 py-1.5 transition cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          </div>
        )}
      </header>

      {/* ── Main content ── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-3 sm:px-4 py-4 space-y-4">
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

        {/* Error banner (non-fatal: already has some blocks displayed) */}
        {error && blocks.length > 0 && (
          <div className="p-3 bg-rose-950/50 border border-rose-700 rounded-lg text-xs text-rose-300 flex justify-between items-center">
            <span>⚠ {error}</span>
            <button onClick={() => refreshWeek()} className="underline font-medium cursor-pointer ml-4">
              Retry
            </button>
          </div>
        )}

        {/* Loading skeleton placeholder while fetching initial data */}
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
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-800 dark:text-emerald-200 flex items-center justify-between gap-3 shadow-xs">
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

        {/* Conflict Alert Banner if any conflicts exist */}
        {conflicts.length > 0 && (
          <div className="p-3.5 bg-rose-950/60 border border-rose-600/70 rounded-xl text-xs text-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md animate-in fade-in duration-200">
            <div className="flex items-center gap-2.5">
              <span className="text-lg">⚠️</span>
              <div>
                <span className="font-semibold text-rose-100 text-sm">
                  {conflicts.length} Schedule Conflict{conflicts.length > 1 ? 's' : ''} Detected
                </span>
                <p className="text-rose-300 text-[11px] mt-0.5">
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

        {/* Week View grid (shown whenever we have blocks, even while refreshing) */}
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
      </main>

      {/* ── Modals ── */}
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

// ─── Page (wraps CalendarProvider with auth-aware props) ─────────────────────

export default function CalendarPage() {
  const router = useRouter();
  const { logout } = useAuthContext();

  return (
    <ProtectedRoute>
      <CalendarProvider
        onUnauthorized={() => {
          logout();
          router.replace('/login');
        }}
      >
        <CalendarContent />
      </CalendarProvider>
    </ProtectedRoute>
  );
}

