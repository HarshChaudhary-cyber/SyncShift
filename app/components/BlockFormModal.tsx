'use client';

import React, { useEffect, useId, useReducer, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { TimeBlock, BlockType, BlockStatus } from './CalendarWeekView';
import { findConflictsFor, calculateDurationMinutes } from '@/lib/schedule';
import TimePicker from '@/components/ui/TimePicker';
import CustomSelect from '@/components/ui/CustomSelect';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BlockFormModalProps {
  /** When set, the modal is open. `undefined` = add-mode, value = edit-mode. */
  initialBlock?: TimeBlock;
  /** Pre-selects the type toggle when opening in add mode. */
  defaultType?: 'class' | 'shift';
  /** All current editable blocks (no conflict blocks) — used for conflict preview. */
  existingBlocks: TimeBlock[];
  /** The ordered list of day-names the calendar is showing, e.g. ['Monday'…'Friday'] */
  days: string[];
  /** Called with the fully-formed block on Save. Parent assigns id for new blocks. */
  onSubmit: (block: Omit<TimeBlock, 'id'> & { id?: string | number }) => void;
  /** Called when the user confirms deletion (edit mode only). */
  onDelete: (blockId: string | number) => void;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  type: BlockType;
  status: 'enrolled' | 'tentative';
  label: string;
  location: string;
  day: string;
  startTime: string;
  endTime: string;
  repeatsWeekly: boolean;
  isOvernight: boolean;
  hourlyWage: string;
}

type FormAction =
  | { field: 'type'; value: BlockType }
  | { field: 'status'; value: 'enrolled' | 'tentative' }
  | { field: 'label' | 'location' | 'day' | 'startTime' | 'endTime' | 'hourlyWage'; value: string }
  | { field: 'repeatsWeekly' | 'isOvernight'; value: boolean };

function formReducer(state: FormState, action: FormAction): FormState {
  // If user sets end time earlier than start time on shifts, auto-suggest overnight
  if (action.field === 'endTime' && state.type === 'shift') {
    const isLate = action.value < state.startTime;
    return { ...state, endTime: action.value, isOvernight: isLate ? true : state.isOvernight };
  }
  return { ...state, [action.field]: action.value };
}

function initialState(
  block: TimeBlock | undefined,
  days: string[],
  defaultType?: 'class' | 'shift',
): FormState {
  if (block) {
    return {
      type: block.type === 'conflict' ? 'class' : block.type,
      status: block.status === 'tentative' ? 'tentative' : 'enrolled',
      label: block.label,
      location: block.subLabel ?? '',
      day: String(block.day),
      startTime: block.startTime,
      endTime: block.endTime,
      repeatsWeekly: block.repeatsWeekly ?? true,
      isOvernight: Boolean(
        block.isOvernight || (block.endTime && block.startTime && block.endTime < block.startTime),
      ),
      hourlyWage: block.hourlyWage != null ? String(block.hourlyWage) : '',
    };
  }
  return {
    type: defaultType ?? 'class',
    status: 'enrolled',
    label: '',
    location: '',
    day: days[0] ?? 'Monday',
    startTime: '09:00',
    endTime: '10:00',
    repeatsWeekly: true,
    isOvernight: false,
    hourlyWage: '',
  };
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

interface FormErrors {
  label?: string;
  startTime?: string;
  endTime?: string;
}

function validate(state: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!state.label.trim()) errors.label = 'Name is required';
  if (!state.startTime) errors.startTime = 'Start time is required';
  if (!state.endTime) errors.endTime = 'End time is required';

  if (state.startTime && state.endTime && state.endTime <= state.startTime && !state.isOvernight) {
    if (state.type === 'shift') {
      errors.endTime = 'End time is before start time. Turn on "Overnight shift" if crossing midnight.';
    } else {
      errors.endTime = 'End time must be after start time';
    }
  }
  return errors;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const inputBase =
  'w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-input)] ' +
  'px-3 py-2 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] ' +
  'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-colors';

const inputError =
  '!border-rose-500 focus:!ring-rose-500';

interface FieldProps {
  label: string;
  error?: string;
  htmlFor: string;
  children: React.ReactNode;
}

function Field({ label, error, htmlFor, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
        {label}
      </label>
      {children}
      {error && (
        <span className="text-xs text-rose-500 dark:text-rose-400">{error}</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function BlockFormModal({
  initialBlock,
  defaultType,
  existingBlocks,
  days,
  onSubmit,
  onDelete,
  onClose,
}: BlockFormModalProps) {
  const uid = useId();
  const isEdit = initialBlock !== undefined;
  const [form, dispatch] = useReducer(formReducer, initialState(initialBlock, days, defaultType));
  const [errors, setErrors] = useState<FormErrors>({});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Focus the name field on open
  const labelRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const t = setTimeout(() => labelRef.current?.focus(), 80);
    return () => clearTimeout(t);
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // ── Conflict preview (computed whenever form changes) ──────────────────
  const conflictingBlocks = React.useMemo(() => {
    if (!form.startTime || !form.endTime) return [];
    if (form.endTime <= form.startTime && !form.isOvernight) return [];

    const candidate: TimeBlock = {
      id: initialBlock?.id,
      day: form.day,
      startTime: form.startTime,
      endTime: form.endTime,
      type: form.type,
      status: form.status,
      isOvernight: form.isOvernight,
      label: form.label || '(unnamed)',
    };
    return findConflictsFor(candidate, existingBlocks);
  }, [form.day, form.startTime, form.endTime, form.type, form.status, form.isOvernight, form.label, existingBlocks, initialBlock?.id]);

  // ── Re-validate on change after first submission attempt ──────────────
  useEffect(() => {
    if (submitted) setErrors(validate(form));
  }, [form, submitted]);

  // ── Handlers ──────────────────────────────────────────────────────────
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    const errs = validate(form);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    const wageNum = parseFloat(form.hourlyWage);
    const isOvernightFinal = form.isOvernight || form.endTime < form.startTime;
    const duration = calculateDurationMinutes(form.startTime, form.endTime, isOvernightFinal);

    const block: Omit<TimeBlock, 'id'> & { id?: string | number } = {
      id: initialBlock?.id,
      day: form.day,
      startTime: form.startTime,
      endTime: form.endTime,
      type: form.type,
      status: form.status,
      isOvernight: isOvernightFinal,
      durationMinutes: duration,
      hourlyWage: !isNaN(wageNum) && wageNum > 0 ? wageNum : undefined,
      label: form.label.trim(),
      subLabel: form.location.trim() || undefined,
      repeatsWeekly: form.repeatsWeekly,
    };
    onSubmit(block);
  }

  function handleDelete() {
    if (initialBlock?.id != null) {
      onDelete(initialBlock.id);
    }
  }

  // ── Type toggle colours ────────────────────────────────────────────────
  const typeAccent = {
    class: {
      active: 'bg-blue-600 text-white',
      inactive: 'text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40',
    },
    shift: {
      active: 'bg-emerald-600 text-white',
      inactive: 'text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40',
    },
  };

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Backdrop blur */}
      <motion.div
        className="absolute inset-0 bg-[var(--modal-overlay)] backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        aria-hidden="true"
      />

      {/* Modal card */}
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={isEdit ? 'Edit block' : 'Add new block'}
        className="relative w-full h-full sm:h-auto sm:max-w-md rounded-none sm:rounded-2xl border-0 sm:border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] shadow-2xl shadow-black/30 flex flex-col max-h-full sm:max-h-[90vh] overflow-hidden"
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.97 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4 border-b border-[var(--border-color)] shrink-0">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            {isEdit ? 'Edit block' : 'New block'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors p-1.5 rounded-md cursor-pointer"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate className="flex flex-col flex-1 min-h-0">
          <div className="px-4 sm:px-5 py-3.5 sm:py-4 space-y-3.5 flex-1 overflow-y-auto">

            {/* ── Type toggle ──────────────────────────────────────────── */}
            <div className="flex rounded-lg border border-[var(--border-color)] overflow-hidden text-xs font-medium">
              {(['class', 'shift'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => dispatch({ field: 'type', value: t })}
                  className={`flex-1 py-2 transition-colors capitalize ${
                    form.type === t
                      ? typeAccent[t].active
                      : typeAccent[t].inactive
                  }`}
                >
                  {t === 'class' ? '🎓 Class' : '💼 Shift'}
                </button>
              ))}
            </div>

            {/* ── What-If Sandbox / Status Selector ────────────────────── */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs">
              <div>
                <span className="font-medium text-[var(--text-primary)]">
                  Mode
                </span>
                <p className="text-[10px] text-[var(--text-muted)]">
                  {form.status === 'enrolled' ? 'Active in your schedule' : 'Sandbox preview (doesn’t lock hours)'}
                </p>
              </div>
              <div className="flex rounded-md border border-[var(--border-color)] overflow-hidden text-[11px] font-medium">
                <button
                  type="button"
                  onClick={() => dispatch({ field: 'status', value: 'enrolled' })}
                  className={`px-2.5 py-1 transition-colors ${
                    form.status === 'enrolled'
                      ? 'bg-[var(--text-primary)] text-[var(--bg-primary)] font-semibold'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--border-color)]'
                  }`}
                >
                  Enrolled
                </button>
                <button
                  type="button"
                  onClick={() => dispatch({ field: 'status', value: 'tentative' })}
                  className={`px-2.5 py-1 transition-colors ${
                    form.status === 'tentative'
                      ? 'bg-amber-500 text-white font-semibold'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--border-color)]'
                  }`}
                >
                  What-If
                </button>
              </div>
            </div>

            {/* ── Name ─────────────────────────────────────────────────── */}
            <Field label="Name" error={errors.label} htmlFor={`${uid}-label`}>
              <input
                ref={labelRef}
                id={`${uid}-label`}
                type="text"
                placeholder={form.type === 'class' ? 'e.g. CS 210: Data Structures' : 'e.g. Campus Library Desk'}
                value={form.label}
                onChange={(e) => dispatch({ field: 'label', value: e.target.value })}
                className={`${inputBase} ${errors.label ? inputError : ''}`}
              />
            </Field>

            {/* ── Location ─────────────────────────────────────────────── */}
            <Field
              label={form.type === 'class' ? 'Room / Section (optional)' : 'Location (optional)'}
              htmlFor={`${uid}-location`}
            >
              <input
                id={`${uid}-location`}
                type="text"
                placeholder={form.type === 'class' ? 'e.g. Room 302, Prof. Sharma' : 'e.g. Student Services Bldg'}
                value={form.location}
                onChange={(e) => dispatch({ field: 'location', value: e.target.value })}
                className={inputBase}
              />
            </Field>

            {/* ── Day ──────────────────────────────────────────────────── */}
            <Field label="Day of week" htmlFor={`${uid}-day`}>
              <CustomSelect
                id={`${uid}-day`}
                options={days.map((d) => ({ value: d, label: d }))}
                value={form.day}
                onChange={(val) => dispatch({ field: 'day', value: String(val) })}
                size="sm"
              />
            </Field>

            {/* ── Time row ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start time" error={errors.startTime} htmlFor={`${uid}-start`}>
                <TimePicker
                  id={`${uid}-start`}
                  value={form.startTime}
                  onChange={(val) => dispatch({ field: 'startTime', value: val })}
                  error={Boolean(errors.startTime)}
                />
              </Field>
              <Field label="End time" error={errors.endTime} htmlFor={`${uid}-end`}>
                <TimePicker
                  id={`${uid}-end`}
                  value={form.endTime}
                  onChange={(val) => dispatch({ field: 'endTime', value: val })}
                  error={Boolean(errors.endTime)}
                />
              </Field>
            </div>

            {/* ── Shift extras: Overnight toggle & Hourly wage ─────────── */}
            {form.type === 'shift' && (
              <div className="grid grid-cols-2 gap-3 items-end pt-1">
                <Field label="Hourly Wage ($/hr)" htmlFor={`${uid}-wage`}>
                  <input
                    id={`${uid}-wage`}
                    type="number"
                    step="0.50"
                    min="0"
                    placeholder="e.g. 17.50"
                    value={form.hourlyWage}
                    onChange={(e) => dispatch({ field: 'hourlyWage', value: e.target.value })}
                    className={inputBase}
                  />
                </Field>

                <div className="pb-1.5">
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-zinc-700 dark:text-zinc-300 select-none">
                    <input
                      type="checkbox"
                      checked={form.isOvernight}
                      onChange={(e) => dispatch({ field: 'isOvernight', value: e.target.checked })}
                      className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                    />
                    <span>🌙 Overnight shift</span>
                  </label>
                  <span className="text-[10px] text-zinc-400 block ml-6">
                    Crosses midnight (+1 day)
                  </span>
                </div>
              </div>
            )}

            {/* ── Repeats weekly toggle ─────────────────────────────────── */}
            <div className="flex items-center justify-between py-1">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
                Repeats weekly
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={form.repeatsWeekly}
                onClick={() => dispatch({ field: 'repeatsWeekly', value: !form.repeatsWeekly })}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1 ${
                  form.repeatsWeekly
                    ? 'bg-indigo-600'
                    : 'bg-zinc-300 dark:bg-zinc-600'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform ${
                    form.repeatsWeekly ? 'translate-x-4' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* ── Conflict warning ─────────────────────────────────────── */}
            <AnimatePresence>
              {conflictingBlocks.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.18 }}
                  className="overflow-hidden"
                >
                  <div className="flex gap-2.5 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/50 px-3 py-2.5">
                    <svg
                      className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <div className="text-xs text-amber-800 dark:text-amber-200">
                      <span className="font-semibold">Schedule conflict: </span>
                      overlaps with{' '}
                      <span className="font-medium underline">
                        {conflictingBlocks.map((b) => b.label).join(', ')}
                      </span>
                      . You can still save it; conflicts will be highlighted in red.
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </div>

          {/* ── Footer ─────────────────────────────────────────────────── */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--border-color)] bg-[var(--bg-secondary)]">
            {/* Delete button (edit mode only) */}
            {isEdit ? (
              showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-rose-600 dark:text-rose-400 font-medium">
                    Delete?
                  </span>
                  <button
                    type="button"
                    onClick={handleDelete}
                    className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-600 hover:bg-rose-700 text-white transition-colors"
                  >
                    Yes, delete
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(false)}
                    className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 font-medium transition-colors"
                >
                  Delete block
                </button>
              )
            ) : (
              <div /> /* spacer */
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 text-xs font-medium rounded-lg bg-[var(--accent-primary)] hover:bg-[var(--accent-hover)] text-white shadow-sm transition-all active:scale-[0.98]"
              >
                {isEdit ? 'Save changes' : 'Add block'}
              </button>
            </div>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
export default BlockFormModal;
