'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useCalendar } from '@/context/CalendarContext';
import { BlockOut } from '@/lib/api';
import { useAddBlock } from '@/hooks/useAddBlock';

// ─── Types ───────────────────────────────────────────────────────────────────

interface FormValues {
  type: 'class' | 'shift';
  title: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location: string;
  course_id: string;          // "" = no course selected
  hourly_wage: string;
  is_flexible: boolean;
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
  defaultType?: 'class' | 'shift';
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
  'w-full px-3 py-2 bg-neutral-950 border border-neutral-700 rounded-lg text-sm text-neutral-100 ' +
  'focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/40 transition placeholder-neutral-500';

const inpSm =
  'w-full px-2.5 py-1.5 bg-neutral-950 border border-neutral-700 rounded-lg text-xs text-neutral-100 ' +
  'focus:border-blue-500 focus:outline-none transition placeholder-neutral-500';

// ─── Component ───────────────────────────────────────────────────────────────

export default function BlockModal({
  isOpen,
  initialBlock,
  defaultType = 'class',
  preFill,
  onClose,
}: BlockModalProps) {
  const { weekStart, deleteBlock } = useCalendar();
  const { courses, coursesLoading, createCourse, submitBlock } = useAddBlock();

  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Inline new-course form
  const [showNewCourse, setShowNewCourse] = useState(false);
  const [newCourse, setNewCourse] = useState<NewCourseForm>({ code: '', name: '', color: '#3b82f6' });
  const [newCourseError, setNewCourseError] = useState<string | null>(null);
  const [creatingCourse, setCreatingCourse] = useState(false);

  // Conflict warning state
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);
  const [pendingSubmit, setPendingSubmit] = useState<ReturnType<typeof buildPayload> | null>(null);

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
  const isTimeInvalid = Boolean(startTime && endTime && endTime <= startTime);

  // Reset form whenever modal opens
  useEffect(() => {
    if (!isOpen) return;
    setServerError(null);
    setConflictWarning(null);
    setPendingSubmit(null);
    setShowNewCourse(false);
    setNewCourse({ code: '', name: '', color: '#3b82f6' });
    setNewCourseError(null);
    setSaving(false);

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
    });

    // Auto-focus title input
    setTimeout(() => titleRef.current?.focus(), 60);
  }, [isOpen, initialBlock, defaultType, preFill, reset]);

  if (!isOpen) return null;

  // ── Helpers ──────────────────────────────────────────────────────────────

  function buildPayload(data: FormValues) {
    return {
      type: data.type,
      title: data.title.trim(),
      day_of_week: Number(data.day_of_week),
      start_time: data.start_time,
      end_time: data.end_time,
      location: data.location?.trim() || null,
      effective_from: todayStr(),
      effective_until: null,
      course_id: data.type === 'class' && data.course_id ? Number(data.course_id) : null,
      hourly_wage:
        data.type === 'shift' && data.hourly_wage
          ? parseFloat(data.hourly_wage)
          : null,
      is_flexible: data.type === 'shift' ? data.is_flexible : false,
    };
  }

  // ── Submit ───────────────────────────────────────────────────────────────

  const doSubmit = async (payload: ReturnType<typeof buildPayload>) => {
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
    if (isTimeInvalid) return;
    await doSubmit(buildPayload(data));
  });

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

  // ── Delete ────────────────────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!initialBlock) return;
    await deleteBlock(initialBlock.id);
    onClose();
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const isClass = selectedType === 'class';
  const title = isEdit
    ? `Edit ${isClass ? 'Class' : 'Shift'}`
    : isClass
    ? '+ Add Class'
    : '+ Add Shift';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-[500px] bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl text-neutral-100 flex flex-col max-h-[90vh]">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-800 shrink-0">
          <h2 className="text-sm font-semibold tracking-wide">{title}</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-full text-neutral-400 hover:bg-neutral-800 hover:text-white transition cursor-pointer text-base"
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

          {/* Conflict warning overlay */}
          {conflictWarning ? (
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
                <div className="flex rounded-lg border border-neutral-700 overflow-hidden text-xs font-medium">
                  {(['class', 'shift'] as const).map((t) => (
                    <label
                      key={t}
                      className={`flex-1 text-center py-2 cursor-pointer transition select-none ${
                        selectedType === t
                          ? t === 'class'
                            ? 'bg-blue-600 text-white'
                            : 'bg-emerald-600 text-white'
                          : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-750'
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
                  <select
                    {...register('day_of_week', { valueAsNumber: true })}
                    className={inpSm + ' py-2'}
                  >
                    {DAYS.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
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
                  <input
                    type="time"
                    {...register('start_time', { required: 'Start time is required' })}
                    className={inpSm + ' py-2'}
                  />
                  {errors.start_time && (
                    <p className="text-[11px] text-rose-400 mt-0.5">{errors.start_time.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    End Time <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="time"
                    {...register('end_time', { required: 'End time is required' })}
                    className={inpSm + ' py-2'}
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

              {/* ── Class-only: course dropdown ── */}
              {isClass && (
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5 font-medium">
                    Course
                  </label>
                  {coursesLoading ? (
                    <div className="text-xs text-neutral-500 py-2">Loading courses…</div>
                  ) : (
                    <select
                      {...register('course_id')}
                      className={inpSm + ' py-2'}
                    >
                      <option value="">— None / standalone —</option>
                      {courses.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.code} · {c.name}
                        </option>
                      ))}
                      <option value="__new__">+ New course…</option>
                    </select>
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
        {!conflictWarning && (
          <div className="flex items-center justify-between px-5 py-3.5 border-t border-neutral-800 shrink-0">
            {isEdit ? (
              <button
                type="button"
                onClick={handleDelete}
                className="text-xs text-rose-400 hover:text-rose-300 transition cursor-pointer font-medium"
              >
                🗑 Delete
              </button>
            ) : (
              <div />
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-xs transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="block-form"
                disabled={isTimeInvalid || saving}
                className={`px-5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                  isClass
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
