'use client';

import React, { useEffect, useState } from 'react';
import { api, CourseOut, StudyTask } from '@/lib/api';
import DatePicker from '@/components/ui/DatePicker';
import CustomSelect from '@/components/ui/CustomSelect';

interface AddTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated: (task: StudyTask) => void;
}

export default function AddTaskModal({
  isOpen,
  onClose,
  onTaskCreated,
}: AddTaskModalProps) {
  const [title, setTitle] = useState('');
  const [courseId, setCourseId] = useState<string>('');
  const [totalHours, setTotalHours] = useState<number>(4.0);
  const [deadline, setDeadline] = useState<string>('');
  const [priority, setPriority] = useState<'high' | 'medium' | 'low'>('medium');
  const [preferredDuration, setPreferredDuration] = useState<number>(90);
  const [courses, setCourses] = useState<CourseOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Default minimum date is tomorrow
  const todayStr = new Date().toISOString().slice(0, 10);

  useEffect(() => {
    if (isOpen) {
      setTitle('');
      setCourseId('');
      setTotalHours(4.0);
      setPriority('medium');
      setPreferredDuration(90);
      // Set default deadline 5 days ahead
      const d = new Date();
      d.setDate(d.getDate() + 5);
      setDeadline(d.toISOString().slice(0, 10));
      setError(null);

      // Fetch courses
      api.getCourses()
        .then((res) => setCourses(res))
        .catch(() => setCourses([]));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Please provide a task or assignment title.');
      return;
    }

    if (!totalHours || totalHours <= 0) {
      setError('Study hours needed must be greater than 0.');
      return;
    }

    if (!deadline) {
      setError('Please select a valid deadline date.');
      return;
    }

    if (deadline < todayStr) {
      setError('Deadline date cannot be in the past.');
      return;
    }

    setLoading(true);
    try {
      const created = await api.createTask({
        title: title.trim(),
        course_id: courseId ? parseInt(courseId, 10) : null,
        total_hours_required: totalHours,
        deadline,
        priority,
        preferred_duration: preferredDuration,
      });
      onTaskCreated(created);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to create study task. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[var(--modal-overlay)] backdrop-blur-xs">
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">📖</span>
            <h2 className="text-base font-bold text-[var(--text-primary)]">Add Study Task</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-950/40 border border-red-800/80 rounded-xl text-xs text-red-300">
              ⚠️ {error}
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
              Task or Exam Title *
            </label>
            <input
              type="text"
              placeholder="e.g. DBMS Project, MATH Midterm Revision"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-hidden focus:border-indigo-500 transition"
              required
            />
          </div>

          {/* Course (Optional) */}
          <div>
            <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
              Course (Optional)
            </label>
            <CustomSelect
              options={[
                { value: '', label: 'No Course (General Study)' },
                ...courses.map((c) => ({
                  value: c.id,
                  label: `${c.code} — ${c.name}`,
                })),
              ]}
              value={courseId}
              onChange={(val) => setCourseId(String(val))}
              placeholder="Select course..."
            />
          </div>

          {/* Grid: Hours Needed & Deadline */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
                Hours Needed *
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="100"
                value={totalHours}
                onChange={(e) => setTotalHours(parseFloat(e.target.value) || 0)}
                className="w-full px-3.5 py-2.5 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl text-sm text-[var(--text-primary)] focus:outline-hidden focus:border-indigo-500 transition font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
                Deadline *
              </label>
              <DatePicker
                minDate={todayStr}
                value={deadline || null}
                onChange={(val) => setDeadline(val || '')}
              />
            </div>
          </div>

          {/* Grid: Priority & Preferred Session Duration */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
                Priority
              </label>
              <div className="grid grid-cols-3 gap-1.5 p-1 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl">
                {(['low', 'medium', 'high'] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPriority(p)}
                    className={`py-1.5 text-xs font-semibold rounded-lg capitalize transition cursor-pointer ${
                      priority === p
                        ? p === 'high'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-xs'
                          : p === 'medium'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-xs'
                          : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 shadow-xs'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-1.5">
                Preferred Duration
              </label>
              <CustomSelect
                options={[
                  { value: 45, label: '45 mins' },
                  { value: 60, label: '1 hour' },
                  { value: 90, label: '1.5 hours' },
                  { value: 120, label: '2 hours' },
                ]}
                value={preferredDuration}
                onChange={(val) => setPreferredDuration(Number(val))}
                placeholder="Preferred duration..."
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-3 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] text-[var(--text-secondary)] border border-[var(--border-color)] text-xs font-semibold rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition shadow-md shadow-indigo-950/50 disabled:opacity-50 cursor-pointer"
            >
              {loading ? 'Creating…' : 'Save Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
