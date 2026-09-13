'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useCalendar } from '@/context/CalendarContext';
import { BlockOut } from '@/lib/api';
import { useAddBlock } from '@/hooks/useAddBlock';
import TimePicker from '@/components/ui/TimePicker';
import DatePicker from '@/components/ui/DatePicker';
import CustomSelect from '@/components/ui/CustomSelect';

// ─── Types ───────────────────────────────────────────────────────────────────

interface FormValues {
  type: 'class' | 'shift' | 'study';
  title: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location: string;
  course_id: string;          // "" = no course selected
  hourly_wage: string;
  is_flexible: boolean;
  recurrence_pattern: 'none' | 'weekly' | 'biweekly';
  effective_from?: string | null;
  effective_until?: string | null;
}

interface NewCourseForm {
  code: string;
  name: string;
  color: string;
}

export interface SlotPreFill {
  dayIndex: number;       // 1–5 (Mon–Fri)
  startTime: string;      // "HH:MM"
  endTime: string;        // "HH:MM"
}

interface BlockModalProps {
  isOpen: boolean;
  initialBlock?: BlockOut | null;
  defaultType?: 'class' | 'shift' | 'study';
  preFill?: SlotPreFill | null;
  onClose: () => void;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const DAYS = [
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
];

const PRESET_COLORS = [
  '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b',
  '#ef4444', '#06b6d4', '#f97316', '#ec4899',
];

const todayStr = () => new Date().toISOString().slice(0, 10);

// ─── Shared input class ───────────────────────────────────────────────────────

const inp =
  'w-full px-3 py-2 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg text-base sm:text-sm text-[var(--text-primary)] ' +
  'focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/40 transition placeholder-[var(--text-muted)]';

const inpSm =
  'w-full px-2.5 py-1.5 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg text-base sm:text-xs text-[var(--text-primary)] ' +
  'focus:border-indigo-500 focus:outline-none transition placeholder-[var(--text-muted)]';

// ─── Component ───────────────────────────────────────────────────────────────

export default function BlockModal({
  isOpen,
  initialBlock,
  defaultType = 'class',
  preFill,
  onClose,
}: BlockModalProps) {
  const { weekStart, deleteBlock, duplicateBlock } = useCalendar();
  const { courses, coursesLoading, createCourse, submitBlock } = useAddBlock();

  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Scope dialog state ('edit' | 'delete' | null)
  const [scopeAction, setScopeAction] = useState<'edit' | 'delete' | null>(null);

  // Inline new-course form
  const [showNewCourse, setShowNewCourse] = useState(false);
  const [newCourse, setNewCourse] = useState<NewCourseForm>({ code: '', name: '', color: '#3b82f6' });
  const [newCourseError, setNewCourseError] = useState<string | null>(null);
  const [creatingCourse, setCreatingCourse] = useState(false);

  // Conflict warning state
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);
  const [pendingSubmit, setPendingSubmit] = useState<any>(null);

  const titleRef = useRef<HTMLInputElement>(null);
  const isEdit = Boolean(initialBlock);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    setFocus,
    formState: { errors },
  } = useForm<FormValues>({ mode: 'onChange' });

  const selectedType = watch('type', defaultType);
  const startTime = watch('start_time');
  const endTime = watch('end_time');
  const effectiveFrom = watch('effective_from');
  const effectiveUntil = watch('effective_until');
  const isTimeInvalid = Boolean(startTime && endTime && endTime <= startTime);
  const isDateInvalid = Boolean(effectiveFrom && effectiveUntil && effectiveUntil < effectiveFrom);

  // Reset form whenever modal opens
  useEffect(() => {
    if (!isOpen) return;
    setServerError(null);
    setConflictWarning(null);
    setPendingSubmit(null);
    setScopeAction(null);
    setShowNewCourse(false);
    setNewCourse({ code: '', name: '', color: '#3b82f6' });
    setNewCourseError(null);
    setSaving(false);

    const initialRecurrencePattern: 'none' | 'weekly' | 'biweekly' =
      initialBlock?.is_recurring
        ? initialBlock.recurrence_interval === 2
          ? 'biweekly'
          : 'weekly'
        : initialBlock
        ? 'none'
        : (defaultType === 'class' ? 'weekly' : 'none');

    reset({
      type: initialBlock?.type ?? defaultType,
      title: initialBlock?.title ?? '',
      day_of_week: preFill?.dayIndex ?? initialBlock?.day_of_week ?? 1,
      start_time: preFill?.startTime ?? (initialBlock?.start_time?.slice(0, 5) ?? '09:00'),
      end_time: preFill?.endTime ?? (initialBlock?.end_time?.slice(0, 5) ?? '10:00'),
      location: initialBlock?.location ?? '',
      course_id: initialBlock?.course_id != null ? String(initialBlock.course_id) : '',
      hourly_wage: initialBlock?.hourly_wage != null ? String(initialBlock.hourly_wage) : '',
      is_flexible: initialBlock?.is_flexible !== false, // default true for shifts
      recurrence_pattern: initialRecurrencePattern,
      effective_from: initialBlock?.effective_from ?? todayStr(),
      effective_until: initialBlock?.effective_until ?? null,
    });

    // Auto-focus title input
    setTimeout(() => titleRef.current?.focus(), 60);
  }, [isOpen, initialBlock, defaultType, preFill, reset]);

  if (!isOpen) return null;

  // ── Helpers ──────────────────────────────────────────────────────────────

  function buildPayload(data: FormValues) {
    const isRecurring = data.recurrence_pattern !== 'none';
    const recurrenceInterval = data.recurrence_pattern === 'biweekly' ? 2 : 1;

    return {
      type: data.type,
      title: data.title.trim(),
      day_of_week: Number(data.day_of_week),
      start_time: data.start_time,
      end_time: data.end_time,
      location: data.location?.trim() || null,
      is_recurring: isRecurring,
      recurrence_interval: recurrenceInterval,
      effective_from: data.effective_from || todayStr(),
      effective_until: data.effective_until || null,
      course_id: data.type === 'class' && data.course_id ? Number(data.course_id) : null,
      hourly_wage:
        data.type === 'shift' && data.hourly_wage
          ? parseFloat(data.hourly_wage)
          : null,
      is_flexible: data.type === 'shift' || data.type === 'study' ? data.is_flexible : false,
      study_task_id: initialBlock?.study_task_id ?? null,
    };
  }

  // ── Submit ───────────────────────────────────────────────────────────────

  const doSubmit = async (payload: any) => {
    setSaving(true);
    setServerError(null);
    try {
      await submitBlock(payload, initialBlock?.id);
      onClose();
    } catch (err: unknown) {
      const apiErr = err as { status?: number; message?: string };
      if (apiErr.status === 422 || apiErr.status === 409) {
        setConflictWarning(apiErr.message ?? 'Schedule overlap detected. Add anyway?');
        setPendingSubmit(payload);
      } else {
        setServerError((err as Error).message || 'Failed to save. Please try again.');
        // Focus first visible error field
        setTimeout(() => setFocus('title'), 50);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSave = handleSubmit(async (data) => {
    if (isTimeInvalid || isDateInvalid) return;
    const payload = buildPayload(data);
    if (isEdit && initialBlock?.is_recurring) {
      setPendingSubmit(payload);
      setScopeAction('edit');
      return;
    }
    await doSubmit(payload);
  });

  const handleApplyScope = async (scope: 'this' | 'future' | 'all') => {
    if (!initialBlock) return;
    setSaving(true);
    setServerError(null);
    try {
      if (scopeAction === 'edit') {
        const payloadWithScope = {
          ...(pendingSubmit || buildPayload(watch())),
          scope,
          occurrence_date: initialBlock.occurrence_date || undefined,
        };
        await submitBlock(payloadWithScope, initialBlock.id);
        onClose();
      } else if (scopeAction === 'delete') {
        await deleteBlock(initialBlock.id, scope, initialBlock.occurrence_date || undefined);
        onClose();
      }
    } catch (err: unknown) {
      setServerError((err as Error).message || 'Action failed. Please try again.');
      setScopeAction(null);
    } finally {
      setSaving(false);
    }
  };

  const handleForceConfirm = async () => {
    if (!pendingSubmit) return;
    setSaving(true);
    try {
      await submitBlock(pendingSubmit, initialBlock?.id);
      onClose();
    } catch (err: unknown) {
      setServerError((err as Error).message ?? 'Could not force-add block.');
      setConflictWarning(null);
    } finally {
      setSaving(false);
    }
  };

  // ── New-course inline creation ─────────────────────────────────────────────

  const handleCreateCourse = async () => {
    if (!newCourse.code.trim() || !newCourse.name.trim()) {
      setNewCourseError('Code and name are required.');
      return;
    }
    setCreatingCourse(true);
    setNewCourseError(null);
    try {
      const created = await createCourse({
        code: newCourse.code.trim().toUpperCase(),
        name: newCourse.name.trim(),
        color: newCourse.color,
      });
      setValue('course_id', String(created.id));
      setShowNewCourse(false);
      setNewCourse({ code: '', name: '', color: '#3b82f6' });
    } catch (err: unknown) {
      setNewCourseError((err as Error).message ?? 'Failed to create course.');
    } finally {
      setCreatingCourse(false);
    }
  };

  // ── Delete & Duplicate ───────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!initialBlock) return;
    if (initialBlock.is_recurring) {
      setScopeAction('delete');
      return;
    }
    await deleteBlock(initialBlock.id);
    onClose();
  };

  const handleDuplicate = async () => {
    if (!initialBlock) return;
    setSaving(true);
    try {
      await duplicateBlock(initialBlock.id);
      onClose();
    } catch (err: unknown) {
      setServerError((err as Error).message || 'Failed to duplicate block');
    } finally {
      setSaving(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const isClass = selectedType === 'class';
  const isStudy = selectedType === 'study';
  const title = isEdit
    ? isStudy
      ? '📖 Edit Study Block'
      : `Edit ${isClass ? 'Class' : 'Shift'}`
    : isClass
    ? '+ Add Class'
    : '+ Add Shift';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-[var(--modal-overlay)] backdrop-blur-sm"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full h-full sm:h-auto sm:max-w-[500px] bg-[var(--bg-card)] sm:border border-[var(--border-color)] rounded-none sm:rounded-2xl shadow-2xl text-[var(--text-primary)] flex flex-col max-h-full sm:max-h-[90vh]">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4 border-b border-[var(--border-color)] shrink-0">
          <h2 className="text-sm font-semibold tracking-wide text-[var(--text-primary)]">{title}</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full text-[var(--text-muted)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer text-base"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">

          {/* Server error */}
          {serverError && (
            <div className="p-3 bg-rose-950/70 border border-rose-600/60 rounded-lg text-xs text-rose-200 leading-relaxed">
              ⚠ {serverError}
            </div>
          )}

          {/* Scope choice dialog overlay for recurring edit/delete */}
          {scopeAction ? (
            <div className="p-4 bg-indigo-950/40 border border-indigo-500/40 rounded-xl space-y-4">
              <div>
                <div className="flex items-center gap-2 text-indigo-300 font-bold text-sm">
                  <span>🔁</span>
                  <span>{scopeAction === 'edit' ? 'Edit Recurring Event' : 'Delete Recurring Event'}</span>
                </div>
                <p className="text-xs text-indigo-200/80 mt-1">
                  {scopeAction === 'edit'
                    ? `Choose how to apply your changes to "${initialBlock?.title}":`
                    : `Choose which occurrences of "${initialBlock?.title}" to delete:`}
                </p>
              </div>

              <div className="space-y-2">
                {/* Option 1: This event only */}
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => handleApplyScope('this')}
                  className="w-full text-left p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500 transition cursor-pointer group"
                >
                  <div className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400 flex items-center justify-between">
                    <span>This event only</span>
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">
                      {initialBlock?.occurrence_date || 'this occurrence'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    {scopeAction === 'edit'
                      ? 'Modifies only this occurrence. Other weeks remain unchanged.'
                      : 'Cancels only this occurrence. Other weeks stay on your schedule.'}
                  </p>
                </button>

                {/* Option 2: This and future */}
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => handleApplyScope('future')}
                  className="w-full text-left p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500 transition cursor-pointer group"
                >
                  <div className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400">
                    This and future events
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    {scopeAction === 'edit'
                      ? 'Applies changes to this occurrence and all future dates in the series.'
                      : 'Ends the series before this date. Past occurrences are kept.'}
                  </p>
                </button>

                {/* Option 3: Entire series */}
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => handleApplyScope('all')}
                  className="w-full text-left p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500 transition cursor-pointer group"
                >
                  <div className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400">
                    Entire series
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    {scopeAction === 'edit'
                      ? 'Updates the entire series across the semester.'
                      : 'Deletes all past and future occurrences of this recurring event.'}
                  </p>
                </button>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="button"
                  onClick={() => setScopeAction(null)}
                  className="px-3 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : conflictWarning ? (
            <div className="p-4 bg-amber-950/50 border border-amber-500/50 rounded-xl text-xs space-y-3">
              <p className="font-semibold text-amber-300">⚠ Schedule Conflict</p>
              <p className="text-amber-200 leading-relaxed">{conflictWarning}</p>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => { setConflictWarning(null); setPendingSubmit(null); }}
                  className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-xs transition cursor-pointer"
                >
                  Go Back
                </button>
                <button
                  type="button"
                  onClick={handleForceConfirm}
                  disabled={saving}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg text-xs font-medium transition cursor-pointer"
                >
                  {saving ? 'Saving…' : 'Add Anyway'}
                </button>
              </div>
            </div>
          ) : (
            <form id="block-form" onSubmit={handleSave} noValidate className="space-y-4">

              {/* ── Type Toggle ── */}
              {!isEdit && (
                <div className="flex rounded-lg border border-[var(--border-color)] overflow-hidden text-xs font-medium">
                  {(['class', 'shift'] as const).map((t) => (
                    <label
                      key={t}
                      className={`flex-1 text-center py-2 cursor-pointer transition select-none ${
                        selectedType === t
                          ? t === 'class'
                            ? 'bg-blue-600 text-white'
                            : 'bg-emerald-600 text-white'
                          : 'bg-[var(--bg-input)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]'
                      }`}
                    >
                      <input
                        type="radio"
                        value={t}
                        className="sr-only"
                        {...register('type')}
                      />
                      {t === 'class' ? '🎓 Class' : '💼 Shift'}
                    </label>
                  ))}
                </div>
              )}

              {/* ── Title ── */}
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                  Title <span className="text-rose-400">*</span>
                </label>
                <input
                  {...register('title', { required: 'Title is required' })}
                  ref={(e) => {
                    register('title').ref(e);
                    (titleRef as React.MutableRefObject<HTMLInputElement | null>).current = e;
                  }}
                  className={inp}
                  placeholder={isClass ? 'e.g. CS 210: Data Structures' : 'e.g. Campus Library Desk'}
                  autoComplete="off"
                />
                {errors.title && (
                  <p className="text-[11px] text-rose-400 mt-1">{errors.title.message}</p>
                )}
              </div>

              {/* ── Day + Location ── */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Day <span className="text-rose-400">*</span>
                  </label>
                  <CustomSelect
                    options={DAYS}
                    value={watch('day_of_week')}
                    onChange={(val) => setValue('day_of_week', Number(val), { shouldDirty: true, shouldValidate: true })}
                    size="sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Location
                  </label>
                  <input
                    {...register('location')}
                    className={inpSm}
                    placeholder="Room / Building"
                    autoComplete="off"
                  />
                </div>
              </div>

              {/* ── Start / End time ── */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Start Time <span className="text-rose-400">*</span>
                  </label>
                  <TimePicker
                    value={startTime}
                    onChange={(val) => setValue('start_time', val, { shouldValidate: true })}
                    error={Boolean(errors.start_time || isTimeInvalid)}
                  />
                  {errors.start_time && (
                    <p className="text-[11px] text-rose-400 mt-0.5">{errors.start_time.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    End Time <span className="text-rose-400">*</span>
                  </label>
                  <TimePicker
                    value={endTime}
                    onChange={(val) => setValue('end_time', val, { shouldValidate: true })}
                    error={Boolean(errors.end_time || isTimeInvalid)}
                  />
                  {errors.end_time && (
                    <p className="text-[11px] text-rose-400 mt-0.5">{errors.end_time.message}</p>
                  )}
                </div>
              </div>
              {isTimeInvalid && (
                <p className="text-[11px] text-rose-400 -mt-2 flex items-center gap-1">
                  <span>⚠</span> End time must be after start time
                </p>
              )}

              {/* ── Recurrence Pattern ── */}
              <div>
                <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                  Recurrence
                </label>
                <div className="grid grid-cols-3 gap-2 text-xs font-medium">
                  {[
                    { id: 'weekly', label: '🔁 Weekly', desc: 'Every week' },
                    { id: 'biweekly', label: '2️⃣ Biweekly', desc: 'Every 2 wks' },
                    { id: 'none', label: '📅 One-off', desc: 'Single event' },
                  ].map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() =>
                        setValue('recurrence_pattern', item.id as any, {
                          shouldDirty: true,
                        })
                      }
                      className={`p-2 rounded-lg border text-center transition cursor-pointer ${
                        watch('recurrence_pattern') === item.id
                          ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 font-semibold ring-1 ring-indigo-500/40'
                          : 'bg-[var(--bg-input)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]'
                      }`}
                    >
                      <div className="text-xs font-bold">{item.label}</div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{item.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Effective Dates (Semester / Schedule Window) ── */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Effective From
                  </label>
                  <DatePicker
                    value={effectiveFrom ?? null}
                    onChange={(val) => setValue('effective_from', val, { shouldValidate: true })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Effective Until
                  </label>
                  <DatePicker
                    value={effectiveUntil ?? null}
                    onChange={(val) => setValue('effective_until', val, { shouldValidate: true })}
                    nullable
                    minDate={effectiveFrom ?? undefined}
                    error={Boolean(isDateInvalid)}
                  />
                </div>
              </div>
              {isDateInvalid && (
                <p className="text-[11px] text-rose-400 -mt-2 flex items-center gap-1">
                  <span>⚠</span> End date must be on or after start date
                </p>
              )}

              {/* ── Class-only: course dropdown ── */}
              {isClass && (
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Course
                  </label>
                  {coursesLoading ? (
                    <div className="text-xs text-neutral-500 py-2">Loading courses…</div>
                  ) : (
                    <CustomSelect
                      options={[
                        { value: '', label: '— None / standalone —' },
                        ...courses.map((c) => ({
                          value: String(c.id),
                          label: `${c.code} · ${c.name}`,
                          icon: (
                            <span
                              className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                              style={{ backgroundColor: c.color || '#3b82f6' }}
                            />
                          ),
                        })),
                        { value: '__new__', label: '+ New course…' },
                      ]}
                      value={watch('course_id') ?? ''}
                      onChange={(val) => {
                        setValue('course_id', String(val), { shouldDirty: true, shouldValidate: true });
                        if (String(val) === '__new__') {
                          setShowNewCourse(true);
                        }
                      }}
                      size="sm"
                    />
                  )}

                  {/* Watch for "new course" selection */}
                  {watch('course_id') === '__new__' && !showNewCourse && (
                    <button
                      type="button"
                      onClick={() => { setShowNewCourse(true); setValue('course_id', ''); }}
                      className="mt-2 text-xs text-blue-400 hover:text-blue-300 underline transition cursor-pointer"
                    >
                      Open new course form →
                    </button>
                  )}

                  {/* Inline new-course form */}
                  {showNewCourse && (
                    <div className="mt-3 p-3 bg-neutral-800/60 border border-neutral-700 rounded-xl space-y-3">
                      <p className="text-xs font-semibold text-neutral-300">Create New Course</p>

                      {newCourseError && (
                        <p className="text-[11px] text-rose-400">{newCourseError}</p>
                      )}

                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-[11px] text-neutral-400 mb-1">Code *</label>
                          <input
                            value={newCourse.code}
                            onChange={(e) => setNewCourse((p) => ({ ...p, code: e.target.value }))}
                            className={inpSm}
                            placeholder="CS101"
                            maxLength={16}
                            autoComplete="off"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] text-neutral-400 mb-1">Name *</label>
                          <input
                            value={newCourse.name}
                            onChange={(e) => setNewCourse((p) => ({ ...p, name: e.target.value }))}
                            className={inpSm}
                            placeholder="Intro to CS"
                            autoComplete="off"
                          />
                        </div>
                      </div>

                      {/* Color picker */}
                      <div>
                        <label className="block text-[11px] text-neutral-400 mb-1.5">Color</label>
                        <div className="flex items-center gap-2 flex-wrap">
                          {PRESET_COLORS.map((c) => (
                            <button
                              key={c}
                              type="button"
                              onClick={() => setNewCourse((p) => ({ ...p, color: c }))}
                              style={{ backgroundColor: c }}
                              className={`w-6 h-6 rounded-full shrink-0 cursor-pointer transition-transform hover:scale-110 ${
                                newCourse.color === c ? 'ring-2 ring-white ring-offset-1 ring-offset-neutral-800 scale-110' : ''
                              }`}
                              aria-label={`Color ${c}`}
                            />
                          ))}
                          <input
                            type="color"
                            value={newCourse.color}
                            onChange={(e) => setNewCourse((p) => ({ ...p, color: e.target.value }))}
                            className="w-7 h-7 rounded cursor-pointer bg-transparent border-0 p-0"
                            title="Custom color"
                          />
                        </div>
                      </div>

                      <div className="flex gap-2 justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => { setShowNewCourse(false); setNewCourseError(null); }}
                          className="px-2.5 py-1 text-xs bg-neutral-700 hover:bg-neutral-600 rounded-lg transition cursor-pointer"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleCreateCourse}
                          disabled={creatingCourse}
                          className="px-2.5 py-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg font-medium transition cursor-pointer"
                        >
                          {creatingCourse ? 'Creating…' : 'Create Course'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Shift-only fields ── */}
              {!isClass && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                      Hourly Wage ($/hr)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm pointer-events-none">$</span>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        {...register('hourly_wage')}
                        className={inpSm + ' pl-6'}
                        placeholder="e.g. 15.50"
                      />
                    </div>
                  </div>

                  <label className="flex items-center gap-3 cursor-pointer group select-none">
                    <div className="relative">
                      <input
                        type="checkbox"
                        {...register('is_flexible')}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-neutral-700 peer-checked:bg-emerald-600 rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-neutral-200 group-hover:text-white transition">
                        I can move this shift
                      </p>
                      <p className="text-[11px] text-neutral-500">
                        Marks shift as flexible for scheduling
                      </p>
                    </div>
                  </label>
                </div>
              )}

            </form>
          )}
        </div>

        {/* ── Footer ── */}
        {!conflictWarning && !scopeAction && (
          <div className="flex items-center justify-between px-5 py-3.5 border-t border-[var(--border-color)] shrink-0 bg-[var(--bg-secondary)] sm:rounded-b-2xl">
            {isEdit ? (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleDelete}
                  className="text-xs text-rose-500 hover:text-rose-600 transition cursor-pointer font-medium"
                >
                  🗑 Delete
                </button>
                <button
                  type="button"
                  onClick={handleDuplicate}
                  disabled={saving}
                  className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer font-medium disabled:opacity-50"
                >
                  📋 Duplicate
                </button>
              </div>
            ) : (
              <div />
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="block-form"
                disabled={isTimeInvalid || saving}
                className={`px-5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                  isStudy
                    ? 'bg-purple-600 hover:bg-purple-500 text-white'
                    : isClass
                    ? 'bg-blue-600 hover:bg-blue-500 text-white'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                }`}
              >
                {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Block'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
