'use client';

import React, { useState, useEffect } from 'react';
import { api, PlanPreviewResponse, PlanSessionSuggested, StudyTask } from '@/lib/api';
import TimePicker from '@/components/ui/TimePicker';

interface PlanPreviewModalProps {
  isOpen: boolean;
  task: StudyTask | null;
  plan: PlanPreviewResponse | null;
  onClose: () => void;
  onPlanConfirmed: (updatedTask: StudyTask) => void;
}

interface EditableSession extends PlanSessionSuggested {
  selected: boolean;
}

export default function PlanPreviewModal({
  isOpen,
  task,
  plan,
  onClose,
  onPlanConfirmed,
}: PlanPreviewModalProps) {
  const [sessions, setSessions] = useState<EditableSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && plan) {
      setSessions(
        plan.suggested.map((s) => ({
          ...s,
          selected: true,
        }))
      );
      setError(null);
    }
  }, [isOpen, plan]);

  if (!isOpen || !task || !plan) return null;

  const toggleSelect = (tempId: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.temp_id === tempId ? { ...s, selected: !s.selected } : s))
    );
  };

  const updateTime = (tempId: string, field: 'start_time' | 'end_time', value: string) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.temp_id === tempId) {
          const updated = { ...s, [field]: value };
          // Recalculate duration
          try {
            const [sh, sm] = updated.start_time.split(':').map(Number);
            const [eh, em] = updated.end_time.split(':').map(Number);
            const dur = (eh * 60 + em) - (sh * 60 + sm);
            if (dur > 0) {
              updated.duration_hours = Math.round((dur / 60) * 100) / 100;
            }
          } catch {
            // Keep existing duration
          }
          return updated;
        }
        return s;
      })
    );
  };

  const selectedSessions = sessions.filter((s) => s.selected);
  const totalSelectedHours = selectedSessions.reduce((sum, s) => sum + s.duration_hours, 0);

  const handleConfirm = async () => {
    if (selectedSessions.length === 0) {
      setError('Please select at least one study session to confirm.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        approved_blocks: selectedSessions.map((s) => ({
          temp_id: s.temp_id,
          day_of_week: s.day_of_week,
          start_time: s.start_time,
          end_time: s.end_time,
          date: s.date,
        })),
      };

      const confirmedTask = await api.confirmTaskPlan(task.id, payload);
      onPlanConfirmed(confirmedTask);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to confirm study plan. Check for clashes with classes.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--modal-overlay)] backdrop-blur-xs">
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">✨</span>
              <h2 className="text-base font-bold text-[var(--text-primary)]">Suggested Study Plan</h2>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              {task.title} · Needs {task.total_hours_required}h before {task.deadline}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {/* Error Message */}
          {error && (
            <div className="p-3 bg-rose-50 dark:bg-red-950/40 border border-rose-200 dark:border-red-800/80 rounded-xl text-xs text-rose-700 dark:text-red-300">
              ⚠️ {error}
            </div>
          )}

          {/* Warning Banner if short on free time */}
          {plan.short_by_hours && plan.short_by_hours > 0 && (
            <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-800 dark:text-amber-200 text-xs space-y-1.5">
              <div className="flex items-center gap-2 font-bold">
                <span className="text-base shrink-0">⚠️</span>
                <span>Not Enough Available Free Time</span>
              </div>
              <p className="leading-relaxed">
                Available: <strong>{plan.hours_scheduled}h</strong> · Required: <strong>{task.total_hours_required}h</strong> · Remaining gap: <strong className="text-amber-600 dark:text-amber-300">{plan.short_by_hours}h</strong>. Consider adjusting your goal or deadline.
              </p>
            </div>
          )}

          {/* Sessions List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider px-1">
              <span>Suggested Slots ({sessions.length})</span>
              <span>{Math.round(totalSelectedHours * 10) / 10}h selected</span>
            </div>

            {sessions.length === 0 ? (
              <div className="p-6 text-center text-[var(--text-muted)] text-sm bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)]">
                No free study gaps found before this deadline. Try clearing schedule items or extending the deadline.
              </div>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.temp_id}
                  className={`p-3.5 rounded-xl border transition space-y-2.5 ${
                    s.selected
                      ? 'bg-[var(--study-bg)] border-[var(--study-border)] text-[var(--text-primary)] shadow-sm'
                      : 'bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-muted)] opacity-60'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    {/* Left: Checkbox, Day, Time, Score */}
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={s.selected}
                        onChange={() => toggleSelect(s.temp_id)}
                        className="w-4 h-4 mt-0.5 rounded text-purple-600 bg-[var(--bg-input)] border-[var(--border-color)] focus:ring-purple-500 cursor-pointer"
                      />

                      <div>
                        <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2 flex-wrap">
                          <span>{s.day_name}</span>
                          <span className="text-[11px] font-mono text-[var(--text-muted)] font-normal">
                            ({s.date})
                          </span>
                          {s.score !== undefined && (
                            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30">
                              Score {s.score}
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-[var(--study-text)] font-medium block mt-0.5">
                          {s.duration_hours}h session · 📖 Self-study
                        </span>
                      </div>
                    </div>

                    {/* Right: Editable Time Range Inputs & Individual Add */}
                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <div className="flex items-center gap-1.5 w-44 sm:w-48">
                        <TimePicker
                          value={s.start_time.slice(0, 5)}
                          disabled={!s.selected}
                          onChange={(val) => updateTime(s.temp_id, 'start_time', val)}
                        />
                        <span className="text-[var(--text-muted)] text-xs">–</span>
                        <TimePicker
                          value={s.end_time.slice(0, 5)}
                          disabled={!s.selected}
                          onChange={(val) => updateTime(s.temp_id, 'end_time', val)}
                        />
                      </div>

                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            setLoading(true);
                            const updatedTask = await api.addPlanSlot(task.id, {
                              temp_id: s.temp_id,
                              day_of_week: s.day_of_week,
                              start_time: s.start_time,
                              end_time: s.end_time,
                              date: s.date,
                            });
                            onPlanConfirmed(updatedTask);
                            onClose();
                          } catch (err: any) {
                            setError(err?.message || 'Failed to add study session');
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading}
                        className="px-2.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold shrink-0 transition cursor-pointer shadow-xs disabled:opacity-50"
                        title="Add only this session to calendar"
                      >
                        + Add to calendar
                      </button>
                    </div>
                  </div>

                  {/* Reasons list */}
                  {s.reasons && s.reasons.length > 0 && (
                    <div className="pt-2 border-t border-[var(--border-color)]/50 flex flex-wrap items-center gap-1.5">
                      {s.reasons.map((r, rIdx) => (
                        <span
                          key={rIdx}
                          className="text-[10px] px-2 py-0.5 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] flex items-center gap-1"
                        >
                          <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                          <span>{r}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center justify-between shrink-0">
          <span className="text-xs text-[var(--text-muted)]">
            {selectedSessions.length} session{selectedSessions.length === 1 ? '' : 's'} ready ({Math.round(totalSelectedHours * 10) / 10}h)
          </span>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-[var(--bg-card)] hover:bg-[var(--border-hover)] text-[var(--text-secondary)] border border-[var(--border-color)] text-xs font-semibold rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={loading || selectedSessions.length === 0}
              className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-xl transition shadow-md shadow-purple-950/50 disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            >
              <span>Confirm & Add All to Calendar</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
