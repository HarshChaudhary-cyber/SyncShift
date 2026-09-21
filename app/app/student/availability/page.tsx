'use client';

import React, { useState, useEffect } from 'react';
import { api, getErrorMessage, StudentAvailabilitySlot } from '@/lib/api';
import { showSuccessToast, showErrorToast } from '@/lib/toast';

const DAYS_OF_WEEK = [
  { id: 0, name: 'Monday', short: 'Mon' },
  { id: 1, name: 'Tuesday', short: 'Tue' },
  { id: 2, name: 'Wednesday', short: 'Wed' },
  { id: 3, name: 'Thursday', short: 'Thu' },
  { id: 4, name: 'Friday', short: 'Fri' },
  { id: 5, name: 'Saturday', short: 'Sat' },
  { id: 6, name: 'Sunday', short: 'Sun' },
];

export default function StudentAvailabilityPage() {
  const [slots, setSlots] = useState<StudentAvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeDay, setActiveDay] = useState<number>(0);

  // Load existing availability
  useEffect(() => {
    async function loadAvailability() {
      try {
        setLoading(true);
        const data = await api.getMyAvailability();
        // Normalize time strings to HH:MM
        const normalized = data.map((s) => ({
          ...s,
          start_time: s.start_time.slice(0, 5),
          end_time: s.end_time.slice(0, 5),
        }));
        setSlots(normalized);
      } catch (err) {
        showErrorToast(getErrorMessage(err, 'Failed to load weekly availability'));
      } finally {
        setLoading(false);
      }
    }
    loadAvailability();
  }, []);

  // Add slot to a specific day
  const handleAddSlot = (day: number) => {
    const newSlot: StudentAvailabilitySlot = {
      day_of_week: day,
      start_time: '09:00',
      end_time: '17:00',
      is_available: true,
      note: '',
    };
    setSlots([...slots, newSlot]);
  };

  // Remove slot
  const handleRemoveSlot = (index: number) => {
    setSlots(slots.filter((_, i) => i !== index));
  };

  // Update slot field
  const handleUpdateSlot = (index: number, field: keyof StudentAvailabilitySlot, value: any) => {
    const updated = [...slots];
    updated[index] = { ...updated[index], [field]: value };
    setSlots(updated);
  };

  // Template: Standard 9am-5pm weekdays
  const applyWeekdayTemplate = () => {
    const weekdaySlots: StudentAvailabilitySlot[] = [0, 1, 2, 3, 4].map((day) => ({
      day_of_week: day,
      start_time: '09:00',
      end_time: '17:00',
      is_available: true,
      note: 'Standard Weekday Hours',
    }));
    setSlots(weekdaySlots);
    showSuccessToast('Template applied: Mon-Fri 09:00-17:00');
  };

  // Template: Clear all
  const clearAllSlots = () => {
    setSlots([]);
  };

  // Validation
  const validateSlots = (): string | null => {
    for (let i = 0; i < slots.length; i++) {
      const s = slots[i];
      if (!s.start_time || !s.end_time) {
        return 'All slots must have valid start and end times.';
      }
      if (s.start_time >= s.end_time) {
        const dayName = DAYS_OF_WEEK.find((d) => d.id === s.day_of_week)?.name;
        return `On ${dayName}: Start time (${s.start_time}) must be before end time (${s.end_time}).`;
      }
    }

    // Check overlap within same day
    for (let day = 0; day < 7; day++) {
      const daySlots = slots.filter((s) => s.day_of_week === day);
      for (let i = 0; i < daySlots.length; i++) {
        for (let j = i + 1; j < daySlots.length; j++) {
          const a = daySlots[i];
          const b = daySlots[j];
          if (a.start_time < b.end_time && b.start_time < a.end_time) {
            const dayName = DAYS_OF_WEEK.find((d) => d.id === day)?.name;
            return `Overlapping time intervals detected on ${dayName} (${a.start_time}-${a.end_time} and ${b.start_time}-${b.end_time}).`;
          }
        }
      }
    }
    return null;
  };

  // Save availability
  const handleSave = async () => {
    const validationError = validateSlots();
    if (validationError) {
      showErrorToast(validationError);
      return;
    }

    try {
      setSaving(true);
      const payloadSlots = slots.map((s) => ({
        day_of_week: s.day_of_week,
        start_time: s.start_time.length === 5 ? `${s.start_time}:00` : s.start_time,
        end_time: s.end_time.length === 5 ? `${s.end_time}:00` : s.end_time,
        is_available: s.is_available,
        note: s.note || null,
      }));
      const saved = await api.saveMyAvailability({ slots: payloadSlots });
      setSlots(
        saved.map((s) => ({
          ...s,
          start_time: s.start_time.slice(0, 5),
          end_time: s.end_time.slice(0, 5),
        }))
      );
      showSuccessToast('Weekly availability saved successfully!');
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to save weekly availability'));
    } finally {
      setSaving(false);
    }
  };

  const getDaySlotCount = (day: number) => slots.filter((s) => s.day_of_week === day).length;

  return (
    <div className="space-y-6">
      {/* Introduction Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🕒</span>
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                Recurring Weekly Availability
              </h2>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-2xl">
              Specify your recurring weekly time ranges when you are available or unavailable for university classes.
              In N5, the timetable optimizer will strictly respect these time bounds alongside your work shifts.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={applyWeekdayTemplate}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-primary)] border border-[var(--border-color)] transition cursor-pointer"
            >
              ⚡ Mon–Fri 9am–5pm
            </button>
            <button
              onClick={clearAllSlots}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition cursor-pointer"
            >
              Clear All
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow hover:shadow-indigo-950/30 transition cursor-pointer flex items-center gap-2"
            >
              {saving && (
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              <span>Save Schedule</span>
            </button>
          </div>
        </div>
      </div>

      {/* Day Selector Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {DAYS_OF_WEEK.map((day) => {
          const count = getDaySlotCount(day.id);
          const isSelected = activeDay === day.id;
          return (
            <button
              key={day.id}
              onClick={() => setActiveDay(day.id)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer shrink-0 ${
                isSelected
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/30'
                  : 'bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <span>{day.name}</span>
              {count > 0 && (
                <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isSelected ? 'bg-black/25 text-white' : 'bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400'
                    }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Active Day Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
          <div>
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              {DAYS_OF_WEEK.find((d) => d.id === activeDay)?.name} Time Intervals
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Define whether you are available or unavailable during specific hours of this day.
            </p>
          </div>

          <button
            onClick={() => handleAddSlot(activeDay)}
            className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5 cursor-pointer shadow-sm"
          >
            <span>+</span>
            <span>Add Interval</span>
          </button>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs">Loading availability intervals...</span>
          </div>
        ) : (
          (() => {
            const daySlotIndices = slots
              .map((s, idx) => ({ ...s, origIndex: idx }))
              .filter((s) => s.day_of_week === activeDay);

            if (daySlotIndices.length === 0) {
              return (
                <div className="py-10 text-center space-y-3 bg-[var(--bg-secondary)]/40 rounded-xl border border-dashed border-[var(--border-color)]">
                  <div className="text-3xl">🗓️</div>
                  <div className="text-xs text-[var(--text-secondary)]">
                    No availability intervals specified for{' '}
                    <strong>{DAYS_OF_WEEK.find((d) => d.id === activeDay)?.name}</strong>.
                  </div>
                  <button
                    onClick={() => handleAddSlot(activeDay)}
                    className="px-3 py-1.5 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--border-color)] text-xs font-semibold text-[var(--text-primary)] border border-[var(--border-color)] transition cursor-pointer"
                  >
                    + Add Interval for this day
                  </button>
                </div>
              );
            }

            return (
              <div className="space-y-3">
                {daySlotIndices.map((slot) => (
                  <div
                    key={slot.origIndex}
                    className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-3 flex-wrap flex-1 w-full sm:w-auto">
                      {/* Status toggle (Available vs Unavailable) */}
                      <button
                        type="button"
                        onClick={() =>
                          handleUpdateSlot(slot.origIndex, 'is_available', !slot.is_available)
                        }
                        className={`px-3 py-1.5 rounded-xl font-semibold transition flex items-center gap-1.5 cursor-pointer ${
                          slot.is_available
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        <span>{slot.is_available ? '✓ Available' : '✕ Unavailable (Blackout)'}</span>
                      </button>

                      {/* Time Range */}
                      <div className="flex items-center gap-2">
                        <label className="text-[11px] text-[var(--text-secondary)]">From:</label>
                        <input
                          type="time"
                          value={slot.start_time}
                          onChange={(e) =>
                            handleUpdateSlot(slot.origIndex, 'start_time', e.target.value)
                          }
                          className="px-2.5 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:outline-none focus:border-indigo-500 transition"
                        />
                        <label className="text-[11px] text-[var(--text-secondary)]">To:</label>
                        <input
                          type="time"
                          value={slot.end_time}
                          onChange={(e) =>
                            handleUpdateSlot(slot.origIndex, 'end_time', e.target.value)
                          }
                          className="px-2.5 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:outline-none focus:border-indigo-500 transition"
                        />
                      </div>

                      {/* Note / Label */}
                      <div className="flex-1 min-w-[140px]">
                        <input
                          type="text"
                          value={slot.note || ''}
                          onChange={(e) =>
                            handleUpdateSlot(slot.origIndex, 'note', e.target.value)
                          }
                          placeholder="Optional note (e.g., Morning commute, Study block)..."
                          className="w-full px-3 py-1.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRemoveSlot(slot.origIndex)}
                      className="px-2.5 py-1.5 rounded-xl text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition cursor-pointer self-end sm:self-auto"
                      title="Delete interval"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            );
          })()
        )}
      </div>

      {/* Overview Grid Across All 7 Days */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm">
        <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
          Weekly Schedule Snapshot
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2">
          {DAYS_OF_WEEK.map((day) => {
            const daySlots = slots.filter((s) => s.day_of_week === day.id);
            return (
              <div
                key={day.id}
                onClick={() => setActiveDay(day.id)}
                className={`p-3 rounded-xl border transition cursor-pointer ${
                  activeDay === day.id
                    ? 'bg-indigo-600/10 border-indigo-500/40'
                    : 'bg-[var(--bg-secondary)] border-[var(--border-color)] hover:border-slate-600'
                }`}
              >
                <div className="font-bold text-xs text-[var(--text-primary)] mb-2 flex items-center justify-between">
                  <span>{day.short}</span>
                  <span className="text-[10px] text-slate-400">{daySlots.length}</span>
                </div>
                <div className="space-y-1">
                  {daySlots.length === 0 ? (
                    <div className="text-[10px] text-slate-500 italic">No restrictions</div>
                  ) : (
                    daySlots.map((s, i) => (
                      <div
                        key={i}
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono truncate ${
                          s.is_available
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                        title={`${s.start_time} - ${s.end_time} (${s.is_available ? 'Available' : 'Unavailable'})`}
                      >
                        {s.start_time}–{s.end_time}
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
