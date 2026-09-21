'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  api,
  getErrorMessage,
  StudentConstraint,
  StudentConstraintCreatePayload,
  StudentPreference,
  StudentPreferenceUpdatePayload,
} from '@/lib/api';
import { showSuccessToast, showErrorToast } from '@/lib/toast';
import CustomSelect from '@/components/ui/CustomSelect';

const PRESET_CONSTRAINTS = [
  {
    type: 'earliest_start',
    label: 'Earliest Class Start Time',
    desc: 'Never schedule any university lecture or lab before this time.',
    defaultParams: { time: '08:30' },
  },
  {
    type: 'latest_end',
    label: 'Latest Class End Time',
    desc: 'Never schedule any university lecture or lab after this time.',
    defaultParams: { time: '18:00' },
  },
  {
    type: 'max_hours_per_day',
    label: 'Maximum Daily Class Hours',
    desc: 'Cap total academic hours scheduled on any single calendar day.',
    defaultParams: { max_hours: 6 },
  },
  {
    type: 'protect_work_shifts',
    label: 'Protect Fixed Work Shifts',
    desc: 'Enforce strict 0% overlap between university classes and non-flexible job shifts.',
    defaultParams: { strict_buffer_minutes: 30 },
  },
];

export default function StudentConstraintsPage() {
  // Constraints state
  const [constraints, setConstraints] = useState<StudentConstraint[]>([]);
  const [loadingConstraints, setLoadingConstraints] = useState(true);

  // Add constraint modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<string>('earliest_start');
  const [constraintName, setConstraintName] = useState<string>('');
  const [constraintParams, setConstraintParams] = useState<Record<string, any>>({ time: '08:30' });
  const [isHard, setIsHard] = useState<boolean>(true);
  const [creatingConstraint, setCreatingConstraint] = useState<boolean>(false);

  // Preferences state
  const [preferences, setPreferences] = useState<StudentPreference | null>(null);
  const [prefForm, setPrefForm] = useState<StudentPreferenceUpdatePayload>({
    preferred_time_of_day: 'morning',
    schedule_density: 'compact',
    max_days_per_week: null,
    prefer_free_days: [],
    break_preference: 'medium',
    work_study_balance_weight: 50,
  });
  const [loadingPrefs, setLoadingPrefs] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Load constraints
  const fetchConstraints = useCallback(async () => {
    try {
      setLoadingConstraints(true);
      const data = await api.getMyConstraints();
      setConstraints(data);
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to load constraints'));
    } finally {
      setLoadingConstraints(false);
    }
  }, []);

  // Load preferences
  const fetchPreferences = useCallback(async () => {
    try {
      setLoadingPrefs(true);
      const data = await api.getMyPreferences();
      setPreferences(data);
      if (data) {
        setPrefForm({
          preferred_time_of_day: data.preferred_time_of_day || 'morning',
          schedule_density: data.schedule_density || 'compact',
          max_days_per_week: data.max_days_per_week,
          prefer_free_days: data.prefer_free_days || [],
          break_preference: data.break_preference || 'medium',
          work_study_balance_weight: data.work_study_balance_weight ?? 50,
        });
      }
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to load preferences'));
    } finally {
      setLoadingPrefs(false);
    }
  }, []);

  useEffect(() => {
    fetchConstraints();
    fetchPreferences();
  }, [fetchConstraints, fetchPreferences]);

  // Handle create constraint
  const handleCreateConstraint = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreatingConstraint(true);
      const payload: StudentConstraintCreatePayload = {
        constraint_type: selectedType,
        name: constraintName.trim() || PRESET_CONSTRAINTS.find((c) => c.type === selectedType)?.label || selectedType,
        parameters: constraintParams,
        is_hard: isHard,
        is_active: true,
      };
      await api.createConstraint(payload);
      showSuccessToast('Constraint added successfully!');
      setAddModalOpen(false);
      setConstraintName('');
      await fetchConstraints();
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to create constraint'));
    } finally {
      setCreatingConstraint(false);
    }
  };

  // Toggle constraint active
  const handleToggleActive = async (constraint: StudentConstraint) => {
    try {
      await api.updateConstraint(constraint.id, {
        is_active: !constraint.is_active,
      });
      setConstraints(
        constraints.map((c) => (c.id === constraint.id ? { ...c, is_active: !c.is_active } : c))
      );
      showSuccessToast(`Constraint ${!constraint.is_active ? 'activated' : 'paused'}.`);
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to update constraint'));
    }
  };

  // Delete constraint
  const handleDeleteConstraint = async (id: number) => {
    try {
      await api.deleteConstraint(id);
      setConstraints(constraints.filter((c) => c.id !== id));
      showSuccessToast('Constraint removed.');
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to delete constraint'));
    }
  };

  // Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingPrefs(true);
      const updated = await api.updateMyPreferences(prefForm);
      setPreferences(updated);
      showSuccessToast('Soft optimization preferences saved!');
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to save preferences'));
    } finally {
      setSavingPrefs(false);
    }
  };

  // Handle free day toggle
  const toggleFreeDay = (day: number) => {
    const current = prefForm.prefer_free_days || [];
    if (current.includes(day)) {
      setPrefForm({ ...prefForm, prefer_free_days: current.filter((d) => d !== day) });
    } else {
      setPrefForm({ ...prefForm, prefer_free_days: [...current, day].sort() });
    }
  };

  // Work-study balance label
  const getBalanceLabel = (val: number) => {
    if (val < 30) return 'Prioritize Class Schedule (Accommodate work around school)';
    if (val > 70) return 'Prioritize Work Shifts (Keep work fixed, fit classes around it)';
    return 'Balanced (Equal weight to academic flow and shift earnings)';
  };

  return (
    <div className="space-y-6">
      {/* 1. Constraint Precedence Hierarchy Banner */}
      <div className="bg-indigo-50/70 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-500/20 rounded-2xl p-5 shadow-sm space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">🛡️</span>
          <h2 className="text-sm font-bold text-indigo-700 dark:text-indigo-300">
            Scheduling Constraint Precedence Hierarchy
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          SyncShift coordinates academic life, employment, and personal goals through an explicit 4-tier constraint system:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-2 text-xs">
          <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-2xs">
            <span className="text-rose-600 dark:text-rose-400 font-bold block mb-1">1. University Hard</span>
            <span className="text-slate-600 dark:text-slate-400 text-[11px]">Room limits, faculty availability, course dependencies.</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-2xs">
            <span className="text-amber-700 dark:text-amber-400 font-bold block mb-1">2. Student Hard</span>
            <span className="text-slate-600 dark:text-slate-400 text-[11px]">Strict cut-off hours, max daily load, non-negotiable blackouts.</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-2xs">
            <span className="text-sky-600 dark:text-sky-400 font-bold block mb-1">3. Fixed Work Shifts</span>
            <span className="text-slate-600 dark:text-slate-400 text-[11px]">Existing job shifts marked non-flexible in calendar.</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 shadow-2xs">
            <span className="text-emerald-600 dark:text-emerald-400 font-bold block mb-1">4. Soft Preferences</span>
            <span className="text-slate-600 dark:text-slate-400 text-[11px]">Preferred time of day, gap duration, compact layout.</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* 2. LEFT: HARD CONSTRAINTS */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base">🔒</span>
                <h3 className="text-sm font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wide">
                  Hard Constraints
                </h3>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                Strict boundaries that the scheduler must <strong>never violate</strong>.
              </p>
            </div>

            <button
              onClick={() => {
                setSelectedType('earliest_start');
                setConstraintParams({ time: '08:30' });
                setConstraintName('');
                setAddModalOpen(true);
              }}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <span>+</span>
              <span>Add Hard Rule</span>
            </button>
          </div>

          {loadingConstraints ? (
            <div className="py-10 flex flex-col items-center justify-center gap-2 text-slate-400">
              <div className="w-6 h-6 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Loading rules...</span>
            </div>
          ) : constraints.length === 0 ? (
            <div className="py-8 text-center space-y-2 bg-[var(--bg-secondary)]/40 rounded-xl border border-dashed border-[var(--border-color)]">
              <div className="text-2xl">📋</div>
              <div className="text-xs text-[var(--text-secondary)]">
                No hard constraints configured yet.
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                Add rules such as no classes before 9am, maximum 6 hours of classes a day, or protecting your work shifts.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {constraints.map((c) => (
                <div
                  key={c.id}
                  className={`p-4 rounded-xl border transition flex items-start justify-between gap-3 text-xs ${
                    c.is_active
                      ? 'bg-[var(--bg-secondary)] border-[var(--border-color)]'
                      : 'bg-slate-100 dark:bg-slate-900/30 border-slate-300 dark:border-slate-800 opacity-60'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-[var(--text-primary)]">
                        {c.name}
                      </span>
                      <span
                        className={`px-2 py-0.2 rounded-full text-[10px] font-mono ${
                          c.is_hard
                            ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20'
                            : 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20'
                        }`}
                      >
                        {c.is_hard ? 'HARD RULE' : 'SOFT RULE'}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                      Type: {c.constraint_type}
                      {c.parameters && Object.keys(c.parameters).length > 0 && (
                        <span> • {JSON.stringify(c.parameters).replace(/[{"}]/g, '')}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleToggleActive(c)}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition cursor-pointer ${
                        c.is_active
                          ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700'
                      }`}
                    >
                      {c.is_active ? 'Active' : 'Paused'}
                    </button>
                    <button
                      onClick={() => handleDeleteConstraint(c.id)}
                      className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition cursor-pointer"
                      title="Delete constraint"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 3. RIGHT: SOFT PREFERENCES */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm space-y-5">
          <div className="pb-3 border-b border-[var(--border-color)]">
            <div className="flex items-center gap-2">
              <span className="text-base">✨</span>
              <h3 className="text-sm font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wide">
                Soft Preferences
              </h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Optimizer targets and weights to tailor your preferred schedule rhythm.
            </p>
          </div>

          {loadingPrefs ? (
            <div className="py-10 flex flex-col items-center justify-center gap-2 text-slate-400">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Loading preferences...</span>
            </div>
          ) : (
            <form onSubmit={handleSavePreferences} className="space-y-4 text-xs">
              {/* Preferred Time of Day */}
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1.5">
                  Preferred Time of Day for Classes
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'morning', label: 'Morning', icon: '🌅', desc: '8am - 12pm' },
                    { id: 'afternoon', label: 'Afternoon', icon: '☀️', desc: '12pm - 5pm' },
                    { id: 'evening', label: 'Evening', icon: '🌙', desc: '5pm+' },
                    { id: 'any', label: 'Any Time', icon: '⚡', desc: 'No preference' },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setPrefForm({ ...prefForm, preferred_time_of_day: t.id })}
                      className={`p-2.5 rounded-xl border text-left transition cursor-pointer ${
                        prefForm.preferred_time_of_day === t.id
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-950/30'
                          : 'bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      <div className="font-bold flex items-center gap-1 text-xs">
                        <span>{t.icon}</span>
                        <span>{t.label}</span>
                      </div>
                      <div className="text-[10px] opacity-80 mt-0.5">{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Schedule Density */}
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1.5">
                  Schedule Density & Grouping
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'compact', label: 'Compact', desc: 'Back-to-back classes' },
                    { id: 'balanced', label: 'Balanced', desc: 'Moderate breaks' },
                    { id: 'spaced', label: 'Spaced', desc: 'Long focus breaks' },
                  ].map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => setPrefForm({ ...prefForm, schedule_density: d.id })}
                      className={`p-2.5 rounded-xl border text-left transition cursor-pointer ${
                        prefForm.schedule_density === d.id
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                          : 'bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      <div className="font-bold text-xs">{d.label}</div>
                      <div className="text-[10px] opacity-80 mt-0.5">{d.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Break Duration */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Ideal Break Length
                  </label>
                  <CustomSelect
                    options={[
                      { value: 'short', label: 'Short (15–20 minutes)' },
                      { value: 'medium', label: 'Medium (30–45 minutes)' },
                      { value: 'long', label: 'Long (60+ minutes)' },
                    ]}
                    value={prefForm.break_preference}
                    onChange={(val) => setPrefForm({ ...prefForm, break_preference: String(val) })}
                    portalTheme="student"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Max Days on Campus / Week
                  </label>
                  <CustomSelect
                    options={[
                      { value: '', label: 'No Maximum (Default)' },
                      { value: '2', label: '2 Days' },
                      { value: '3', label: '3 Days' },
                      { value: '4', label: '4 Days' },
                      { value: '5', label: '5 Days' },
                    ]}
                    value={prefForm.max_days_per_week ? String(prefForm.max_days_per_week) : ''}
                    onChange={(val) =>
                      setPrefForm({
                        ...prefForm,
                        max_days_per_week: val ? Number(val) : null,
                      })
                    }
                    portalTheme="student"
                  />
                </div>
              </div>

              {/* Preferred Free Days */}
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1.5">
                  Preferred Days Off (No Classes)
                </label>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {[
                    { id: 0, label: 'Mon' },
                    { id: 1, label: 'Tue' },
                    { id: 2, label: 'Wed' },
                    { id: 3, label: 'Thu' },
                    { id: 4, label: 'Fri' },
                  ].map((day) => {
                    const isSelected = (prefForm.prefer_free_days || []).includes(day.id);
                    return (
                      <button
                        key={day.id}
                        type="button"
                        onClick={() => toggleFreeDay(day.id)}
                        className={`px-3 py-1.5 rounded-xl font-semibold transition cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-500/40'
                            : 'bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        {isSelected ? `✓ Free ${day.label}` : day.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Work-Study Balance Slider */}
              <div className="pt-2">
                <div className="flex justify-between items-center mb-1">
                  <label className="text-slate-700 dark:text-slate-300 font-semibold">
                    Work / Study Balance Weight
                  </label>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                    {prefForm.work_study_balance_weight}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={prefForm.work_study_balance_weight}
                  onChange={(e) =>
                    setPrefForm({ ...prefForm, work_study_balance_weight: Number(e.target.value) })
                  }
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 italic">
                  {getBalanceLabel(prefForm.work_study_balance_weight || 50)}
                </p>
              </div>

              <div className="pt-3 border-t border-[var(--border-color)] flex justify-end">
                <button
                  type="submit"
                  disabled={savingPrefs}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md hover:shadow-indigo-950/30 transition cursor-pointer flex items-center gap-2"
                >
                  {savingPrefs && (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  )}
                  <span>Save Preferences</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* 4. ADD HARD CONSTRAINT MODAL */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Add Hard Scheduling Constraint
              </h3>
              <button
                onClick={() => setAddModalOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateConstraint} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Constraint Type
                </label>
                <CustomSelect
                  options={[
                    ...PRESET_CONSTRAINTS.map((p) => ({
                      value: p.type,
                      label: p.label,
                      sublabel: p.desc,
                    })),
                    { value: 'custom', label: 'Custom Rule', sublabel: 'Define a customized constraint rule' },
                  ]}
                  value={selectedType}
                  onChange={(val) => {
                    const newType = String(val);
                    setSelectedType(newType);
                    const preset = PRESET_CONSTRAINTS.find((p) => p.type === newType);
                    if (preset) {
                      setConstraintParams(preset.defaultParams);
                      setConstraintName(preset.label);
                    }
                  }}
                  portalTheme="student"
                />
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                  {PRESET_CONSTRAINTS.find((p) => p.type === selectedType)?.desc}
                </p>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Rule Name / Label
                </label>
                <input
                  type="text"
                  value={constraintName}
                  onChange={(e) => setConstraintName(e.target.value)}
                  placeholder="e.g., No classes before 8:30am"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                />
              </div>

              {/* Dynamic parameters depending on type */}
              {(selectedType === 'earliest_start' || selectedType === 'latest_end') && (
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Cut-off Time
                  </label>
                  <input
                    type="time"
                    value={constraintParams.time || '08:30'}
                    onChange={(e) => setConstraintParams({ ...constraintParams, time: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>
              )}

              {selectedType === 'max_hours_per_day' && (
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Maximum Academic Hours
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={constraintParams.max_hours || 6}
                    onChange={(e) =>
                      setConstraintParams({ ...constraintParams, max_hours: Number(e.target.value) })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>
              )}

              {selectedType === 'protect_work_shifts' && (
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Transition Buffer Around Shifts (Minutes)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="15"
                    max="120"
                    value={constraintParams.strict_buffer_minutes || 30}
                    onChange={(e) =>
                      setConstraintParams({
                        ...constraintParams,
                        strict_buffer_minutes: Number(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-color)]">
                <button
                  type="button"
                  onClick={() => setAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-primary)] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingConstraint}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow transition cursor-pointer flex items-center gap-2"
                >
                  {creatingConstraint && (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  )}
                  <span>Add Constraint</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
