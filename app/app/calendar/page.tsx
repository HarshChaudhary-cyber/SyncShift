'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { useAuthContext } from '@/context/AuthContext';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import { BlockOut } from '@/lib/api';
import { showSuccessToast } from '@/lib/toast';
import ProtectedRoute from '@/components/ProtectedRoute';
import SummaryCard from '@/components/calendar/SummaryCard';

import WeekView from '@/components/calendar/WeekView';
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
  const {
    weekStart,
    blocks,
    loading,
    lastUpdated,
    error,
    goToPrevWeek,
    goToNextWeek,
    goToCurrentWeek,
    refreshWeek,
  } = useCalendar();

  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    initialBlock?: BlockOut | null;
    defaultType?: 'class' | 'shift';
    preFill?: SlotPreFill | null;
  }>({ isOpen: false });

  const [importOpen, setImportOpen] = useState(false);

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
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-neutral-400">
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
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center px-4">
        <div className="max-w-sm w-full text-center space-y-4">
          <div className="text-5xl">📡</div>
          <h2 className="text-lg font-semibold text-white">
            {isNetworkError
              ? "Couldn't load your schedule"
              : 'Session expired'}
          </h2>
          <p className="text-sm text-neutral-400">
            {isNetworkError
              ? 'Check your internet connection and try again.'
              : 'Your session has expired. Please sign in again.'}
          </p>
          <div className="flex justify-center gap-3">
            {isNetworkError ? (
              <button
                onClick={() => refreshWeek()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition cursor-pointer"
              >
                Retry
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
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col">

      {/* ── Header ── */}
      <header className="border-b border-neutral-800 bg-neutral-900/60 sticky top-0 z-30 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">

          {/* Left: wordmark + week badge + last-updated */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 text-white font-bold text-lg hover:opacity-80">
              <span className="text-xl">⚡</span>
              <span>SyncShift</span>
            </Link>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono">
              Week of {weekStart}
            </span>
            {lastUpdated && (
              <span className="hidden sm:inline text-[11px] text-neutral-500">
                Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
              </span>
            )}
          </div>

          {/* Right: user email + controls */}
          <div className="flex flex-wrap items-center gap-2">
            {/* User email pill */}
            {user && (
              <span className="hidden md:inline text-xs text-neutral-400 border border-neutral-700 rounded-full px-3 py-1">
                {user.email}
              </span>
            )}

            {/* Week steppers */}
            <div className="flex items-center bg-neutral-800/80 rounded-lg p-0.5 border border-neutral-700/60 text-xs">
              <button onClick={goToPrevWeek} title="Previous week" className="px-2.5 py-1 hover:bg-neutral-700 rounded transition cursor-pointer">
                ◀
              </button>
              <button onClick={goToCurrentWeek} title="Go to current week" className="px-3 py-1 hover:bg-neutral-700 rounded font-medium transition cursor-pointer">
                Today
              </button>
              <button onClick={goToNextWeek} title="Next week" className="px-2.5 py-1 hover:bg-neutral-700 rounded transition cursor-pointer">
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
              className="px-2.5 py-1.5 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg text-xs font-medium text-neutral-200 transition cursor-pointer"
            >
              ↻ Refresh
            </button>

            {/* Import timetable */}
            <button
              onClick={() => setImportOpen(true)}
              className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 rounded-lg text-xs font-medium text-neutral-200 transition cursor-pointer"
            >
              📅 Import Timetable
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
      </header>

      {/* ── Main content ── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-4 space-y-4">
        {/* Weekly summary metrics */}
        <SummaryCard />

        {/* Error banner (non-fatal: already has some blocks displayed) */}
        {error && blocks.length > 0 && (
          <div className="p-3 bg-rose-950/50 border border-rose-700 rounded-lg text-xs text-rose-300 flex justify-between items-center">
            <span>⚠ {error}</span>
            <button onClick={() => refreshWeek()} className="underline font-medium cursor-pointer ml-4">
              Retry
            </button>
          </div>
        )}

        {/* Loading skeleton overlay while fetching (but only if we already have no blocks) */}
        {loading && blocks.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-neutral-500 gap-3">
            <Spinner size={30} className="text-indigo-400" />
            <p className="text-sm">Loading your schedule…</p>
          </div>
        )}

        {/* Loading indicator overlaid when refreshing existing data */}
        {loading && blocks.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <Spinner size={12} className="text-indigo-400" />
            <span>Refreshing…</span>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && blocks.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
            <div className="text-6xl select-none">🗓️</div>
            <h2 className="text-lg font-semibold text-white">Your schedule is empty this week</h2>
            <p className="text-sm text-neutral-400 max-w-xs">
              Add a class or shift to get started, or import your university timetable from a{' '}
              <span className="font-mono text-neutral-300">.ics</span> file.
            </p>
            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setModalState({ isOpen: true, defaultType: 'class' })}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition cursor-pointer"
              >
                + Add Class
              </button>
              <button
                onClick={() => setModalState({ isOpen: true, defaultType: 'shift' })}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg transition cursor-pointer"
              >
                + Add Shift
              </button>
              <button
                onClick={() => setImportOpen(true)}
                className="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-neutral-200 text-sm font-semibold rounded-lg transition cursor-pointer"
              >
                📅 Import .ics
              </button>
            </div>
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

