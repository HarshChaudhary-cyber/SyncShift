'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import CustomSelect from '@/components/ui/CustomSelect';
import {
  api,
  AcademicCourse,
  AcademicCourseCreatePayload,
  Department,
} from '@/lib/api';

export default function CoursesPage() {
  const { institution, isAdmin } = useUniversity();
  const [courses, setCourses] = useState<AcademicCourse[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<AcademicCourse | null>(null);
  const [form, setForm] = useState<AcademicCourseCreatePayload>({
    department_id: 0,
    code: '',
    name: '',
    description: '',
    credits: 3,
    level: 'undergraduate',
    status: 'active',
    min_room_capacity: undefined,
    required_room_type: undefined,
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const [coursesData, deptsData] = await Promise.all([
        api.getAcademicCourses(institution.id, {
          department_id: deptFilter !== 'all' ? Number(deptFilter) : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          search: search.trim() || undefined,
        }),
        api.getDepartments(institution.id),
      ]);
      setCourses(coursesData);
      setDepartments(deptsData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load courses');
    } finally {
      setLoading(false);
    }
  }, [institution, deptFilter, statusFilter, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreateModal = () => {
    setEditingCourse(null);
    setForm({
      department_id: departments.length > 0 ? departments[0].id : 0,
      code: '',
      name: '',
      description: '',
      credits: 3,
      level: 'undergraduate',
      status: 'active',
      min_room_capacity: undefined,
      required_room_type: '',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (course: AcademicCourse) => {
    setEditingCourse(course);
    setForm({
      department_id: course.department_id,
      code: course.code,
      name: course.name,
      description: course.description || '',
      credits: course.credits,
      level: course.level || 'undergraduate',
      status: course.status,
      min_room_capacity: course.min_room_capacity ?? undefined,
      required_room_type: course.required_room_type || '',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.code.trim() || !form.name.trim()) {
      setFormError('Course code and name are required.');
      return;
    }
    if (!form.department_id) {
      setFormError('Please select a department.');
      return;
    }
    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingCourse) {
        await api.updateAcademicCourse(institution.id, editingCourse.id, {
          department_id: form.department_id,
          code: form.code.trim().toUpperCase(),
          name: form.name.trim(),
          description: form.description?.trim() || null,
          credits: Number(form.credits) || 3,
          level: form.level || 'undergraduate',
          status: form.status,
          min_room_capacity: form.min_room_capacity ? Number(form.min_room_capacity) : null,
          required_room_type: form.required_room_type?.trim() || null,
        });
      } else {
        await api.createAcademicCourse(institution.id, {
          department_id: form.department_id,
          code: form.code.trim().toUpperCase(),
          name: form.name.trim(),
          description: form.description?.trim() || undefined,
          credits: Number(form.credits) || 3,
          level: form.level || 'undergraduate',
          status: form.status,
          min_room_capacity: form.min_room_capacity ? Number(form.min_room_capacity) : undefined,
          required_room_type: form.required_room_type?.trim() || undefined,
        });
      }

      setModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Operation failed. Verify course code uniqueness.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (course: AcademicCourse) => {
    if (!institution) return;
    if (!confirm(`Are you sure you want to archive course "${course.code} — ${course.name}"?`)) {
      return;
    }
    try {
      await api.deleteAcademicCourse(institution.id, course.id);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to archive course');
    }
  };

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Courses
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage courses, credit values, levels, and room requirements for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-sm"
          >
            <span>+</span>
            <span>Add Course</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] p-3.5 rounded-xl">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search code or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="w-52">
          <CustomSelect
            options={[
              { value: 'all', label: 'All Departments' },
              ...departments.map((d) => ({
                value: String(d.id),
                label: `${d.name} (${d.code})`,
              })),
            ]}
            value={deptFilter}
            onChange={(val) => setDeptFilter(String(val))}
            size="sm"
            searchable
            portalTheme="university"
          />
        </div>

        <div className="w-40">
          <CustomSelect
            options={[
              { value: 'all', label: 'All Status' },
              { value: 'active', label: 'Active' },
              { value: 'draft', label: 'Draft' },
              { value: 'archived', label: 'Archived' },
            ]}
            value={statusFilter}
            onChange={(val) => setStatusFilter(String(val))}
            size="sm"
            portalTheme="university"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="p-12 text-center text-[var(--text-secondary)]">Loading courses...</div>
      ) : courses.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          <span className="text-4xl">📚</span>
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mt-3">No Courses Found</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-md mx-auto">
            {search || deptFilter !== 'all'
              ? 'No courses match the current filter criteria.'
              : 'Add courses to your department catalog to begin creating section offerings.'}
          </p>
          {isAdmin && (
            <button
              onClick={openCreateModal}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
            >
              Add First Course
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] shadow-sm">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border-color)] bg-[var(--bg-elevated)]/50 text-[var(--text-secondary)] font-medium text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4">Code</th>
                <th className="py-3.5 px-4">Name & Description</th>
                <th className="py-3.5 px-4">Department</th>
                <th className="py-3.5 px-4">Credits / Level</th>
                <th className="py-3.5 px-4">Room Requirements</th>
                <th className="py-3.5 px-4">Status</th>
                {isAdmin && <th className="py-3.5 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-primary)]">
              {courses.map((c) => (
                <tr key={c.id} className="hover:bg-[var(--bg-elevated)]/30 transition">
                  <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                      {c.code}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-[var(--text-primary)]">{c.name}</div>
                    {c.description && (
                      <div className="text-xs text-[var(--text-muted)] line-clamp-1 mt-0.5">
                        {c.description}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-[var(--text-secondary)]">
                    {c.department_name || `Dept #${c.department_id}`}
                  </td>
                  <td className="py-3 px-4 text-[var(--text-secondary)]">
                    <span className="font-medium text-[var(--text-primary)]">{c.credits} cr</span> •{' '}
                    <span className="capitalize text-xs">{c.level || 'undergrad'}</span>
                  </td>
                  <td className="py-3 px-4 text-xs text-[var(--text-secondary)]">
                    {c.required_room_type || c.min_room_capacity ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-color)]">
                        🚪 {c.required_room_type || 'any'} {c.min_room_capacity ? `(${c.min_room_capacity}+ seats)` : ''}
                      </span>
                    ) : (
                      <span className="text-[var(--text-muted)]">Standard</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold capitalize ${
                        c.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : c.status === 'draft'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                  {isAdmin && (
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => openEditModal(c)}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg text-indigo-400 hover:bg-indigo-500/10 transition"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(c)}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg text-rose-400 hover:bg-rose-500/10 transition ml-1"
                      >
                        Archive
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">
                {editingCourse ? 'Edit Course' : 'Create New Course'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition text-lg"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 text-xs rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Course Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CS101"
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Department *
                  </label>
                  <CustomSelect
                    options={departments.map((d) => ({
                      value: String(d.id),
                      label: `${d.name} (${d.code})`,
                    }))}
                    value={form.department_id ? String(form.department_id) : ''}
                    onChange={(val) => setForm({ ...form, department_id: Number(val) })}
                    placeholder="Select Department..."
                    searchable
                    portalTheme="university"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Course Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Introduction to Computer Science"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Credits
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={form.credits}
                    onChange={(e) => setForm({ ...form, credits: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Level
                  </label>
                  <CustomSelect
                    options={[
                      { value: 'undergraduate', label: 'Undergraduate' },
                      { value: 'postgraduate', label: 'Postgraduate' },
                      { value: 'doctorate', label: 'Doctorate' },
                      { value: 'diploma', label: 'Diploma' },
                    ]}
                    value={form.level || 'undergraduate'}
                    onChange={(val) => setForm({ ...form, level: String(val) })}
                    portalTheme="university"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Status
                  </label>
                  <CustomSelect
                    options={[
                      { value: 'active', label: 'Active' },
                      { value: 'draft', label: 'Draft' },
                      { value: 'archived', label: 'Archived' },
                    ]}
                    value={form.status || 'active'}
                    onChange={(val) => setForm({ ...form, status: String(val) })}
                    portalTheme="university"
                  />
                </div>
              </div>

              {/* Resource Requirements for Future Optimization */}
              <div className="border-t border-[var(--border-color)] pt-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
                  Timetable Resource Requirements
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                      Required Room Type
                    </label>
                    <CustomSelect
                      options={[
                        { value: '', label: 'Any Room' },
                        { value: 'classroom', label: 'Classroom' },
                        { value: 'lecture_hall', label: 'Lecture Hall' },
                        { value: 'laboratory', label: 'Laboratory' },
                        { value: 'seminar_room', label: 'Seminar Room' },
                        { value: 'auditorium', label: 'Auditorium' },
                      ]}
                      value={form.required_room_type || ''}
                      onChange={(val) => setForm({ ...form, required_room_type: String(val) })}
                      portalTheme="university"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                      Min Room Capacity
                    </label>
                    <input
                      type="number"
                      min="1"
                      placeholder="e.g. 40"
                      value={form.min_room_capacity || ''}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          min_room_capacity: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                      className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Overview of curriculum and objectives..."
                  value={form.description || ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-color)]">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition"
                >
                  {submitting ? 'Saving...' : editingCourse ? 'Save Changes' : 'Create Course'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
