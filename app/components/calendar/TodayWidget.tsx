'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { api, BlockOut, TodayViewData, ApiError } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';

interface TodayWidgetProps {
  onBlockClick?: (block: BlockOut) => void;
  className?: string;
  refreshTrigger?: unknown;
}

/**
 * Calculates milliseconds until next midnight in the given timezone.
 * Returns at least 1000ms.
 */
function getMsUntilNextMidnight(timeZone: string): number {
  try {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    const parts = formatter.formatToParts(now);
    const partMap: Record<string, string> = {};
    for (const p of parts) {
      partMap[p.type] = p.value;
    }

    const hour = parseInt(partMap.hour || '0', 10);
    const minute = parseInt(partMap.minute || '0', 10);
    const second = parseInt(partMap.second || '0', 10);

    const msSinceMidnight =
      (hour * 3600 + minute * 60 + second) * 1000 + now.getMilliseconds();
    const msInDay = 24 * 60 * 60 * 1000;
    let msUntilMidnight = msInDay - msSinceMidnight;

    if (msUntilMidnight <= 0) {
      msUntilMidnight = msInDay;
    }
    // Add 1.5s buffer so the clock comfortably crosses past 00:00:00
    return msUntilMidnight + 1500;
  } catch {
    const now = new Date();
    const tomorrow = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + 1,
      0,
      0,
      2
    );
    return Math.max(1000, tomorrow.getTime() - now.getTime());
  }
}

/**
 * Formats "YYYY-MM-DD" into "Monday, 7 September"
 */
function formatDisplayDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map((v) => parseInt(v, 10));
    if (!y || !m || !d) return dateStr;
    const dateObj = new Date(y, m - 1, d);
    return new Intl.DateTimeFormat('en-GB', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    }).format(dateObj);
  } catch {
    return dateStr;
  }
}

/**
 * Gets current HH:MM in the specified timezone
 */
function getCurrentTimeStr(timeZone: string): string {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(new Date());
  } catch {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, '0')}:${String(
      now.getMinutes()
    ).padStart(2, '0')}`;
  }
}

/**
 * Gets current YYYY-MM-DD in the specified timezone
 */
function getCurrentDateStr(timeZone: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    return formatter.format(new Date());
  } catch {
    const now = new Date();
    return now.toISOString().slice(0, 10);
  }
}

/**
 * Checks if current time is within block's start and end times
 */
function isBlockActiveNow(
  block: BlockOut,
  currentTimeStr: string,
  isToday: boolean
): boolean {
  if (!isToday) return false;
  const start = block.start_time.slice(0, 5);
  const end = block.end_time.slice(0, 5);

  if (end < start) {
    // Overnight block (e.g. 22:00 -> 02:00)
    return currentTimeStr >= start || currentTimeStr < end;
  }
  return currentTimeStr >= start && currentTimeStr < end;
}

export default function TodayWidget({
  onBlockClick,
  className = '',
  refreshTrigger,
}: TodayWidgetProps) {
  const { user } = useAuthContext();
  const timezone =
    user?.timezone ||
    (typeof Intl !== 'undefined'
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : 'Europe/London');

  const [data, setData] = useState<TodayViewData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [nowTime, setNowTime] = useState<string>('');

  const midnightTimerRef = useRef<NodeJS.Timeout | null>(null);
  const safetyIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const clockIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasErrorRef = useRef<boolean>(false);
  const initialMountRef = useRef<boolean>(true);

  // ── Fetch today's schedule ────────────────────────────────────────────────
  const fetchToday = useCallback(async () => {
    try {
      setError(null);
      hasErrorRef.current = false;
      const res = await api.getToday();
      setData(res);
    } catch (err: unknown) {
      console.error('[TodayWidget] Failed to fetch schedule:', err);
      hasErrorRef.current = true;
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Couldn't load today's schedule");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Keep a stable ref to fetchToday so timer recursion doesn't rebuild effects
  const fetchTodayRef = useRef(fetchToday);
  useEffect(() => {
    fetchTodayRef.current = fetchToday;
  }, [fetchToday]);

  // ── Schedule midnight refresh in user's timezone ─────────────────────────
  const scheduleMidnightRefreshRef = useRef<() => void>(() => {});
  const scheduleMidnightRefresh = useCallback(() => {
    if (midnightTimerRef.current) {
      clearTimeout(midnightTimerRef.current);
    }
    const msUntilMidnight = getMsUntilNextMidnight(timezone);
    midnightTimerRef.current = setTimeout(() => {
      fetchTodayRef.current();
      scheduleMidnightRefreshRef.current(); // Re-arm for the following midnight
    }, msUntilMidnight);
  }, [timezone]);

  useEffect(() => {
    scheduleMidnightRefreshRef.current = scheduleMidnightRefresh;
  }, [scheduleMidnightRefresh]);

  useEffect(() => {
    // Set initial clock time on client mount
    setNowTime(getCurrentTimeStr(timezone));

    // 3a. On component mount: fetch GET /api/v1/today
    fetchToday();

    // 3b. Schedule next refresh at midnight in user's timezone
    scheduleMidnightRefresh();

    // 3c. Safety net: re-fetch every 5 minutes, but ONLY if last fetch succeeded
    safetyIntervalRef.current = setInterval(() => {
      if (!hasErrorRef.current) {
        fetchTodayRef.current();
      }
    }, 5 * 60 * 1000);

    // Live clock ticker every 30 seconds for the "● Now" indicator
    clockIntervalRef.current = setInterval(() => {
      setNowTime(getCurrentTimeStr(timezone));
    }, 30 * 1000);

    // 3d. Re-fetch when the browser tab regains focus OR becomes visible
    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible') {
        setNowTime(getCurrentTimeStr(timezone));
        fetchTodayRef.current();
        scheduleMidnightRefresh();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocus);
    window.addEventListener('focus', handleVisibilityOrFocus);

    // 3e. Clean up ALL timers/listeners on component unmount
    return () => {
      if (midnightTimerRef.current) clearTimeout(midnightTimerRef.current);
      if (safetyIntervalRef.current) clearInterval(safetyIntervalRef.current);
      if (clockIntervalRef.current) clearInterval(clockIntervalRef.current);
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      window.removeEventListener('focus', handleVisibilityOrFocus);
    };
  }, [fetchToday, scheduleMidnightRefresh, timezone]);

  // Re-fetch when external calendar state (lastUpdated) changes
  // Skip the initial mount to avoid double-fetching
  useEffect(() => {
    if (initialMountRef.current) {
      initialMountRef.current = false;
      return;
    }
    if (refreshTrigger !== undefined) {
      fetchTodayRef.current();
    }
  }, [refreshTrigger]);

  // ── Date and "is today" evaluation ────────────────────────────────────────
  const todayInTz = getCurrentDateStr(timezone);
  const isDataActuallyToday = data?.date === todayInTz;

  // ── Loading state ─────────────────────────────────────────────────────────
  if (loading && !data) {
    return (
      <section
        aria-label="Today's Timetable"
        className={`w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 sm:p-5 shadow-sm text-[var(--text-primary)] animate-pulse ${className}`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="h-5 w-48 bg-[var(--bg-secondary)] rounded"></div>
          <div className="h-4 w-16 bg-[var(--bg-secondary)] rounded"></div>
        </div>
        <div className="space-y-3">
          <div className="h-16 bg-[var(--bg-secondary)] rounded-lg"></div>
          <div className="h-16 bg-[var(--bg-secondary)] rounded-lg"></div>
        </div>
        <div className="mt-4 flex items-center justify-between pt-3 border-t border-[var(--border-color)]">
          <p className="text-xs text-[var(--text-secondary)]">Loading today&apos;s schedule…</p>
        </div>
      </section>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (error && !data) {
    return (
      <section
        aria-label="Today's Timetable"
        className={`w-full bg-rose-950/30 border border-rose-900/60 rounded-xl p-4 sm:p-5 text-neutral-200 ${className}`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">⚠️</span>
            <div>
              <h2 className="text-sm font-semibold text-rose-200">
                Couldn&apos;t load today&apos;s schedule
              </h2>
              <p className="text-xs text-rose-300/80 mt-0.5">
                {error || 'Unable to connect to timetable service.'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setLoading(true);
              fetchToday();
            }}
            className="self-start sm:self-auto px-3.5 py-1.5 bg-rose-900/60 hover:bg-rose-800 text-rose-100 text-xs font-medium rounded-lg border border-rose-700/60 transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      </section>
    );
  }

  if (!data) return null;

  const displayDate = formatDisplayDate(data.date);
  const blocks = data.blocks || [];
  const classBlocks = blocks.filter((b) => b.type === 'class');
  const shiftBlocks = blocks.filter((b) => b.type === 'shift');

  // Summary footer pieces
  const summaryParts: string[] = [];
  if (classBlocks.length > 0) {
    summaryParts.push(
      `${classBlocks.length} ${classBlocks.length === 1 ? 'class' : 'classes'} (${data.class_hours}h)`
    );
  }
  if (shiftBlocks.length > 0) {
    summaryParts.push(
      `${shiftBlocks.length} ${shiftBlocks.length === 1 ? 'shift' : 'shifts'} (${data.shift_hours}h)`
    );
  }
  if (data.expected_earnings > 0) {
    const formattedEarnings =
      data.expected_earnings % 1 === 0
        ? data.expected_earnings.toFixed(0)
        : data.expected_earnings.toFixed(2);
    summaryParts.push(`Earns ₹${formattedEarnings}`);
  }

  const summaryFooterText =
    summaryParts.length > 0
      ? summaryParts.join(' · ')
      : 'No scheduled activities';

  return (
    <section
      aria-label="Today's Timetable"
      className={`w-full bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--border-hover)] rounded-xl p-4 sm:p-5 shadow-lg text-[var(--text-primary)] transition-all ${className}`}
    >
      {/* ── Header: Day, Date & Live Badge ─────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)] gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="h-7 w-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 text-sm">
            📅
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 bg-indigo-950/70 border border-indigo-800/50 px-1.5 py-0.5 rounded">
                Today
              </span>
              <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] tracking-tight truncate">
                {displayDate}
              </h2>
            </div>
          </div>
        </div>

        {/* Live timezone time indicator */}
        <div className="text-right shrink-0">
          <span className="text-xs font-mono text-[var(--text-secondary)]" suppressHydrationWarning>
            {nowTime}
          </span>
        </div>
      </div>

      {/* ── Timeline list or Empty State ───────────────────────────────────── */}
      <div className="py-3">
        {blocks.length === 0 ? (
          // Empty state: friendly, encouraging, layout intact
          <div className="py-6 px-4 text-center rounded-lg bg-[var(--bg-secondary)] border border-dashed border-[var(--border-color)] my-1">
            <p className="text-sm font-medium text-[var(--text-primary)]">
              No classes or shifts today 🎉
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Enjoy your free time, relax, or catch up on your studies.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {blocks.map((block) => {
              const isNow = isBlockActiveNow(block, nowTime, isDataActuallyToday);
              const isShift = block.type === 'shift';
              const blockColor = block.color || (isShift ? '#10b981' : '#3b82f6');
              const hasConflict = data.conflicts?.some(
                (c) => c.block_a_id === block.id || c.block_b_id === block.id
              );

              return (
                <div
                  key={block.id}
                  onClick={() => onBlockClick?.(block)}
                  role={onBlockClick ? 'button' : undefined}
                  tabIndex={onBlockClick ? 0 : undefined}
                  style={{
                    borderLeftColor: blockColor,
                    borderLeftWidth: '4px',
                  }}
                  className={`relative rounded-lg border border-[var(--border-color)] p-3 sm:p-3.5 transition-all select-none ${
                    onBlockClick ? 'cursor-pointer hover:border-[var(--border-hover)]' : ''
                  } ${
                    isNow
                      ? 'bg-[var(--bg-secondary)] border-indigo-500/70 shadow-md ring-1 ring-indigo-500/30'
                      : 'bg-[var(--bg-secondary)]/50 hover:bg-[var(--bg-secondary)]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        {/* Class vs Shift badge */}
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            isShift
                              ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                              : 'bg-blue-500/15 text-blue-500 border border-blue-500/30'
                          }`}
                        >
                          <span>{isShift ? '💼 Shift' : '🎓 Class'}</span>
                        </span>

                        {/* "● Now" indicator */}
                        {isNow && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500 text-white animate-pulse shadow-sm">
                            <span className="h-1.5 w-1.5 rounded-full bg-white"></span>
                            NOW
                          </span>
                        )}

                        {/* Conflict tag */}
                        {hasConflict && (
                          <span className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-500 border border-rose-500/30">
                            ⚠️ Conflict
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <h3 className="text-sm font-semibold text-[var(--text-primary)] mt-1.5 truncate">
                        {block.title}
                      </h3>

                      {/* Location & Wage info */}
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[var(--text-secondary)] mt-0.5">
                        {block.location && (
                          <span className="inline-flex items-center gap-1 truncate">
                            <span>📍</span>
                            <span className="truncate">{block.location}</span>
                          </span>
                        )}
                        {isShift && block.hourly_wage != null && (
                          <span className="text-emerald-500 font-mono text-[11px]">
                            ₹{block.hourly_wage}/hr
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Time Range */}
                    <div className="text-right shrink-0">
                      <div className="text-xs sm:text-sm font-mono font-medium text-[var(--text-primary)]">
                        {block.start_time.slice(0, 5)} - {block.end_time.slice(0, 5)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Today's summary footer ─────────────────────────────────────────── */}
      <div className="pt-3 border-t border-[var(--border-color)] flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
        <div className="font-medium text-[var(--text-primary)] truncate">
          {summaryFooterText}
        </div>
        <div className="text-[11px] text-[var(--text-muted)]">
          Auto-updates at midnight
        </div>
      </div>
    </section>
  );
}
