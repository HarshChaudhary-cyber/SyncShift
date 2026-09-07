'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { format, startOfWeek, addWeeks, subWeeks } from 'date-fns';
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

interface CalendarContextType {
  blocks: BlockOut[];
  conflicts: ConflictItem[];
  totals: WeeklyTotals;
  weekStart: string;
  loading: boolean;
  /** ISO string or null — timestamp of the last successful week fetch. */
  lastUpdated: Date | null;
  error: string | null;
  setWeekStart: (date: string) => void;
  goToNextWeek: () => void;
  goToPrevWeek: () => void;
  goToCurrentWeek: () => void;
  refreshWeek: () => Promise<void>;
  refreshConflicts: () => Promise<void>;
  addBlock: (payload: BlockCreatePayload) => Promise<BlockOut>;
  updateBlock: (id: number, payload: BlockUpdatePayload) => Promise<BlockOut>;
  deleteBlock: (id: number) => Promise<void>;
  moveBlock: (id: number, dayOfWeek: number, startTime: string, endTime: string) => Promise<void>;
  resizeBlock: (id: number, endTime: string) => Promise<void>;
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

  // Reload whenever the selected week changes
  useEffect(() => {
    loadWeek(weekStart);
  }, [loadWeek, weekStart]);

  // ── Idle-refetch: attach to the onIdleReturn ref from AuthContext ───────────
  // CalendarProvider receives a ref from the page component so it can register
  // a "reload on idle return" callback without depending on AuthContext directly.
  // (This is wired up in calendar/page.tsx.)

  // ── CRUD actions ───────────────────────────────────────────────────────────

  const addBlock = async (payload: BlockCreatePayload) => {
    const created = await api.createBlock(payload);
    setBlocks((prev) => [...prev, created]);
    await refreshConflicts();
    return created;
  };

  const updateBlock = async (id: number, payload: BlockUpdatePayload) => {
    const updated = await api.updateBlock(id, payload);
    setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, ...updated } : b)));
    await refreshConflicts();
    return updated;
  };

  const deleteBlock = async (id: number) => {
    await api.deleteBlock(id);
    setBlocks((prev) => prev.filter((b) => b.id !== id));
    await refreshConflicts();
  };

  const moveBlock = async (id: number, dayOfWeek: number, startTime: string, endTime: string) => {
    const previousBlock = blocks.find((b) => b.id === id);
    if (!previousBlock) return;

    setBlocks((prev) =>
      prev.map((b) =>
        b.id === id
          ? { ...b, day_of_week: dayOfWeek, start_time: startTime, end_time: endTime, isSaving: true }
          : b
      )
    );

    try {
      const updated = await api.updateBlock(id, {
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
      });

      setBlocks((prev) =>
        prev.map((b) => (b.id === id ? { ...b, ...updated, isSaving: false } : b))
      );
      await refreshConflicts();
    } catch (err: unknown) {
      console.error(`Failed to persist move for block #${id}:`, err);
      setBlocks((prev) =>
        prev.map((b) => (b.id === id ? { ...previousBlock, isSaving: false } : b))
      );
      showErrorToast("Couldn't save move. Please try again.");
      throw err;
    }
  };

  const resizeBlock = async (id: number, endTime: string) => {
    const previousBlock = blocks.find((b) => b.id === id);
    if (!previousBlock) return;

    setBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, end_time: endTime, isSaving: true } : b))
    );

    try {
      const updated = await api.updateBlock(id, { end_time: endTime });
      setBlocks((prev) =>
        prev.map((b) => (b.id === id ? { ...b, ...updated, isSaving: false } : b))
      );
      await refreshConflicts();
    } catch (err: unknown) {
      console.error(`Failed to resize block #${id}:`, err);
      setBlocks((prev) =>
        prev.map((b) => (b.id === id ? { ...previousBlock, isSaving: false } : b))
      );
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
        setWeekStart,
        goToNextWeek: () =>
          setWeekStart((curr) => format(addWeeks(new Date(curr), 1), 'yyyy-MM-dd')),
        goToPrevWeek: () =>
          setWeekStart((curr) => format(subWeeks(new Date(curr), 1), 'yyyy-MM-dd')),
        goToCurrentWeek: () =>
          setWeekStart(format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd')),
        refreshWeek,
        refreshConflicts,
        addBlock,
        updateBlock,
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
