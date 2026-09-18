'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { api, BlockOut, getAuthToken } from '@/lib/api';
import { CalendarProvider } from '@/context/CalendarContext';
import BlockModal from '@/components/calendar/BlockModal';
import { showErrorToast, showSuccessToast } from '@/lib/toast';

function ShiftsContent() {
  const [shifts, setShifts] = useState<BlockOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    editBlock?: BlockOut | null;
  }>({ isOpen: false });

  const fetchShifts = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const allBlocks = await api.getBlocks('shift');
      // Sort upcoming shifts chronologically
      const sorted = (allBlocks || []).sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );
      setShifts(sorted);
    } catch (err) {
      console.warn('Unable to load shifts:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShifts();
  }, [fetchShifts]);

  const handleDelete = async (id: number, title: string) => {
    if (!confirm(`Delete shift "${title}"?`)) return;
    try {
      await api.deleteBlock(id);
      showSuccessToast(`Deleted shift "${title}"`);
      fetchShifts();
    } catch {
      showErrorToast('Failed to delete shift');
    }
  };

  const totalShiftHours = shifts.reduce((acc, s) => {
    const start = new Date(s.start_time).getTime();
    const end = new Date(s.end_time).getTime();
    return acc + Math.max(0, (end - start) / (1000 * 60 * 60));
  }, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">💼</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Work Shifts</h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Track your employment commitments, work limits, and prevent clashes with classes.
          </p>
        </div>
        <button
          onClick={() => setModalState({ isOpen: true })}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-950/20 self-start sm:self-auto"
        >
          + Add Work Shift
        </button>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Total Shifts</p>
          <p className="text-2xl font-black text-[var(--text-primary)] mt-1">{shifts.length}</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Active shift blocks</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Total Hours</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{totalShiftHours.toFixed(1)} hrs</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Scheduled across all shifts</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Privacy Guarantee</p>
          <p className="text-sm font-semibold text-indigo-400 mt-1">100% Private</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Hidden from university faculty & staff</p>
        </div>
      </div>

      {/* Shift List */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Scheduled Shifts</h2>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Loading work shifts…
          </div>
        ) : shifts.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <span className="text-4xl">☕</span>
            <p className="text-sm font-medium text-[var(--text-secondary)]">No work shifts recorded yet.</p>
            <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
              Add your job shifts so SyncShift can protect your working hours and alert you when classes conflict.
            </p>
            <button
              onClick={() => setModalState({ isOpen: true })}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              Add First Shift
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-color)]">
            {shifts.map((shift) => {
              const start = new Date(shift.start_time);
              const end = new Date(shift.end_time);
              const hours = Math.max(0, (end.getTime() - start.getTime()) / (1000 * 60 * 60));

              return (
                <div key={shift.id} className="py-3.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
                      💼
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-[var(--text-primary)]">{shift.title}</h3>
                      <p className="text-xs text-[var(--text-secondary)]">
                        {start.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} ·{' '}
                        {start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} –{' '}
                        {end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({hours.toFixed(1)} hrs)
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setModalState({ isOpen: true, editBlock: shift })}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(shift.id, shift.title)}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition cursor-pointer"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modals */}
      {modalState.isOpen && (
        <BlockModal
          isOpen
          initialBlock={modalState.editBlock || undefined}
          defaultType="shift"
          onClose={() => {
            setModalState({ isOpen: false });
            fetchShifts();
          }}
        />
      )}
    </div>
  );
}

export default function StudentShiftsPage() {
  return (
    <CalendarProvider>
      <ShiftsContent />
    </CalendarProvider>
  );
}
