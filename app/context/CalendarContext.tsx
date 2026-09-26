'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { format, startOfWeek, addWeeks, subWeeks, parseISO } from 'date-fns';
import {
  api,
  ApiError,
  BlockOut,
  ConflictItem,
  WeeklyTotals,
  BlockCreatePayload,
  BlockUpdatePayload,
} from '@/lib/api';
import { showErrorToast } from '@/lib/toast';

// ─── Types ────────────────────────────────────────────────────────────────────

export type CalendarViewMode = '5day' | '7day';

interface CalendarContextType {
  blocks: BlockOut[];
  conflicts: ConflictItem[];
  totals: WeeklyTotals;
  weekStart: string;
  loading: boolean;
  /** ISO string or null — timestamp of the last successful week fetch. */
  lastUpdated: Date | null;
  error: string | null;
  viewMode: CalendarViewMode;
  setViewMode: (mode: CalendarViewMode) => void;
  setWeekStart: (date: string) => void;
  goToNextWeek: () => void;
  goToPrevWeek: () => void;
  goToCurrentWeek: () => void;
  refreshWeek: () => Promise<void>;
  refreshConflicts: () => Promise<void>;
  addBlock: (payload: BlockCreatePayload) => Promise<BlockOut>;
  updateBlock: (id: number, payload: BlockUpdatePayload) => Promise<BlockOut>;
  duplicateBlock: (id: number, daysOffset?: number) => Promise<BlockOut>;
  deleteBlock: (id: number, scope?: 'this' | 'future' | 'all', occurrenceDate?: string) => Promise<void>;
  moveBlock: (id: number, dayOfWeek: number, startTime: string, endTime: string, occurrenceDate?: string, scope?: 'this' | 'future' | 'all') => Promise<void>;
  resizeBlock: (id: number, endTime: string, occurrenceDate?: string, scope?: 'this' | 'future' | 'all') => Promise<void>;
}

const defaultTotals: WeeklyTotals = {
  shift_hours: 0,
  class_hours: 0,
  expected_earnings: 0,
  over_limit: false,
};

// ─── Context ──────────────────────────────────────────────────────────────────

const CalendarContext = createContext<CalendarContextType | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

interface CalendarProviderProps {
  children: React.ReactNode;
  /**
   * Called when any API call returns 401. The parent (calendar page) is
   * responsible for redirecting to /login and clearing the auth token.
   */
  onUnauthorized?: () => void;
}

export function CalendarProvider({ children, onUnauthorized }: CalendarProviderProps) {
  const [weekStart, setWeekStart] = useState<string>(() =>
    format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd')
  );
  const [viewMode, setViewMode] = useState<CalendarViewMode>('7day');
  const [blocks, setBlocks] = useState<BlockOut[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [totals, setTotals] = useState<WeeklyTotals>(defaultTotals);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Stable ref for onUnauthorized so it never invalidates callbacks
  const onUnauthorizedRef = useRef(onUnauthorized);
  useEffect(() => { onUnauthorizedRef.current = onUnauthorized; }, [onUnauthorized]);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const refreshConflicts = useCallback(async () => {
    try {
      const res = await api.getConflicts(weekStart);
      setConflicts(res.conflicts || []);
      if (res.weekly_totals) setTotals(res.weekly_totals);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorizedRef.current?.();
      }
      console.error('Failed to refetch conflicts', err);
    }
  }, [weekStart]);

  const loadWeek = useCallback(async (start: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWeekView(start);
      setBlocks(data.blocks || []);
      setConflicts(data.conflicts || []);
      setTotals(data.totals || defaultTotals);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorizedRef.current?.();
        return; // skip setting error — parent handles redirect
      }
      setError((err as Error).message || 'Failed to fetch schedule');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshWeek = useCallback(() => loadWeek(weekStart), [loadWeek, weekStart]);

  useEffect(() => {
    const refresh = () => { void refreshWeek(); };
    window.addEventListener('syncshift:schedule-updated', refresh);
    return () => window.removeEventListener('syncshift:schedule-updated', refresh);
  }, [refreshWeek]);

  // Reload whenever the selected week changes
  useEffect(() => {
    loadWeek(weekStart);
  }, [loadWeek, weekStart]);

  // ── CRUD actions ───────────────────────────────────────────────────────────

  const addBlock = async (payload: BlockCreatePayload) => {
    const created = await api.createBlock(payload);
    await refreshWeek();
    await refreshConflicts();
    return created;
  };

  const updateBlock = async (id: number, payload: BlockUpdatePayload) => {
    const updated = await api.updateBlock(id, payload);
    await refreshWeek();
    await refreshConflicts();
    return updated;
  };

  const duplicateBlock = async (id: number, daysOffset: number = 0) => {
    const duplicated = await api.duplicateBlock(id, daysOffset);
    await refreshWeek();
    await refreshConflicts();
    return duplicated;
  };

  const deleteBlock = async (id: number, scope: 'this' | 'future' | 'all' = 'all', occurrenceDate?: string) => {
    await api.deleteBlock(id, scope, occurrenceDate);
    await refreshWeek();
    await refreshConflicts();
  };

  const moveBlock = async (
    id: number,
    dayOfWeek: number,
    startTime: string,
    endTime: string,
    occurrenceDate?: string,
    scope: 'this' | 'future' | 'all' = 'this'
  ) => {
    const previousBlock = blocks.find((b) => b.id === id);
    if (!previousBlock) return;

    setBlocks((prev) =>
      prev.map((b) =>
        b.id === id && (!occurrenceDate || b.occurrence_date === occurrenceDate)
          ? { ...b, day_of_week: dayOfWeek, start_time: startTime, end_time: endTime, isSaving: true }
          : b
      )
    );

    try {
      await api.updateBlock(id, {
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
        occurrence_date: occurrenceDate,
        scope,
      });
      await refreshWeek();
      await refreshConflicts();
    } catch (err: unknown) {
      console.error(`Failed to persist move for block #${id}:`, err);
      await refreshWeek();
      showErrorToast("Couldn't save move. Please try again.");
      throw err;
    }
  };

  const resizeBlock = async (
    id: number,
    endTime: string,
    occurrenceDate?: string,
    scope: 'this' | 'future' | 'all' = 'this'
  ) => {
    const previousBlock = blocks.find((b) => b.id === id);
    if (!previousBlock) return;

    setBlocks((prev) =>
      prev.map((b) =>
        b.id === id && (!occurrenceDate || b.occurrence_date === occurrenceDate)
          ? { ...b, end_time: endTime, isSaving: true }
          : b
      )
    );

    try {
      await api.updateBlock(id, {
        end_time: endTime,
        occurrence_date: occurrenceDate,
        scope,
      });
      await refreshWeek();
      await refreshConflicts();
    } catch (err: unknown) {
      console.error(`Failed to resize block #${id}:`, err);
      await refreshWeek();
      showErrorToast("Couldn't save resize. Please try again.");
      throw err;
    }
  };

  return (
    <CalendarContext.Provider
      value={{
        blocks,
        conflicts,
        totals,
        weekStart,
        loading,
        lastUpdated,
        error,
        viewMode,
        setViewMode,
        setWeekStart,
        goToNextWeek: () =>
          setWeekStart((curr) => format(addWeeks(parseISO(curr), 1), 'yyyy-MM-dd')),
        goToPrevWeek: () =>
          setWeekStart((curr) => format(subWeeks(parseISO(curr), 1), 'yyyy-MM-dd')),
        goToCurrentWeek: () =>
          setWeekStart(format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd')),
        refreshWeek,
        refreshConflicts,
        addBlock,
        updateBlock,
        duplicateBlock,
        deleteBlock,
        moveBlock,
        resizeBlock,
      }}
    >
      {children}
    </CalendarContext.Provider>
  );
}

// ─── Consumer hook ────────────────────────────────────────────────────────────

export function useCalendar() {
  const context = useContext(CalendarContext);
  if (!context) throw new Error('useCalendar must be used within a CalendarProvider');
  return context;
}
