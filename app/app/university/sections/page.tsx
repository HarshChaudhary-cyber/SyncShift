'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import {
  api,
  AcademicCourse,
  AcademicSection,
  AcademicSectionCreatePayload,
  AcademicTerm,
  FacultyProfile,
  FacultyAssignment,
} from '@/lib/api';

export default function SectionsPage() {
  const { institution, isAdmin } = useUniversity();
  const [sections, setSections] = useState<AcademicSection[]>([]);
  const [courses, setCourses] = useState<AcademicCourse[]>([]);
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [facultyList, setFacultyList] = useState<FacultyProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [courseFilter, setCourseFilter] = useState<string>('all');
  const [termFilter, setTermFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Create / Edit Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<AcademicSection | null>(null);
  const [form, setForm] = useState<AcademicSectionCreatePayload>({
    course_id: 0,
    academic_term_id: 0,
    section_code: '',
    capacity: 30,
    status: 'active',
    description: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Instructors Modal
  const [instructorModalOpen, setInstructorModalOpen] = useState(false);
  const [managingSection, setManagingSection] = useState<AcademicSection | null>(null);
  const [assigningFacultyId, setAssigningFacultyId] = useState<number>(0);
  const [assigningRole, setAssigningRole] = useState<string>('instructor');
  const [assigningPrimary, setAssigningPrimary] = useState<boolean>(false);
  const [instructorActionLoading, setInstructorActionLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const [sectionsData, coursesData, termsData, facultyData] = await Promise.all([
        api.getSections(institution.id, {
          course_id: courseFilter !== 'all' ? Number(courseFilter) : undefined,
          academic_term_id: termFilter !== 'all' ? Number(termFilter) : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
        }),
        api.getAcademicCourses(institution.id),
        api.getAcademicTerms(institution.id),
        api.getFaculty(institution.id),
      ]);
      setSections(sectionsData);
      setCourses(coursesData);
      setTerms(termsData);
      setFacultyList(facultyData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load sections');
    } finally {
      setLoading(false);
    }
  }, [institution, courseFilter, termFilter, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreateModal = () => {
    setEditingSection(null);
    setForm({
      course_id: courses.length > 0 ? courses[0].id : 0,
      academic_term_id: terms.length > 0 ? terms[0].id : 0,
      section_code: '',
      capacity: 30,
      status: 'active',
      description: '',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (sec: AcademicSection) => {
    setEditingSection(sec);
    setForm({
      course_id: sec.course_id,
      academic_term_id: sec.academic_term_id,
      section_code: sec.section_code,
      capacity: sec.capacity,
      status: sec.status,
      description: sec.description || '',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.section_code.trim()) {
      setFormError('Section code is required.');
      return;
    }
    if (!form.course_id || !form.academic_term_id) {
      setFormError('Course and Academic Term must be selected.');
      return;
    }
    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingSection) {
        await api.updateSection(institution.id, editingSection.id, {
          section_code: form.section_code.trim().toUpperCase(),
          capacity: Number(form.capacity) || 30,
          status: form.status,
          description: form.description?.trim() || null,
        });
      } else {
        await api.createSection(institution.id, {
          course_id: form.course_id,
          academic_term_id: form.academic_term_id,
          section_code: form.section_code.trim().toUpperCase(),
          capacity: Number(form.capacity) || 30,
          status: form.status,
          description: form.description?.trim() || undefined,
        });
      }

      setModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Operation failed. Verify section code uniqueness.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (sec: AcademicSection) => {
    if (!institution) return;
    if (!confirm(`Are you sure you want to cancel/archive section "${sec.section_code}"?`)) {
      return;
    }
    try {
      await api.deleteSection(institution.id, sec.id);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to archive section');
    }
  };

  // Instructors Modal Handlers
  const openInstructorsModal = (sec: AcademicSection) => {
    setManagingSection(sec);
    setAssigningFacultyId(facultyList.length > 0 ? facultyList[0].id : 0);
    setAssigningRole('instructor');
    setAssigningPrimary(false);
    setInstructorModalOpen(true);
  };

  const handleAssignFaculty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !managingSection || !assigningFacultyId) return;

    try {
      setInstructorActionLoading(true);
      await api.assignFacultyToSection(institution.id, managingSection.id, {
        faculty_id: assigningFacultyId,
        role: assigningRole,
        is_primary: assigningPrimary,
      });
      // Refresh section details
      const updated = await api.getSection(institution.id, managingSection.id);
      setManagingSection(updated);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to assign faculty member');
    } finally {
      setInstructorActionLoading(false);
    }
  };

  const handleRemoveFaculty = async (assignmentId: number) => {
    if (!institution || !managingSection) return;
    try {
      setInstructorActionLoading(true);
      await api.removeFacultyFromSection(institution.id, managingSection.id, assignmentId);
      const updated = await api.getSection(institution.id, managingSection.id);
      setManagingSection(updated);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to remove faculty member');
    } finally {
      setInstructorActionLoading(false);
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
            Sections
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage course class sections, student seating capacities, and instructor assignments for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-sm"
          >
            <span>+</span>
            <span>Add Section</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] p-3.5 rounded-xl">
        <div className="w-56">
          <select
            value={courseFilter}
            onChange={(e) => setCourseFilter(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="w-52">
          <select
            value={termFilter}
            onChange={(e) => setTermFilter(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Academic Terms</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.academic_year})
              </option>
            ))}
          </select>
        </div>

        <div className="w-36">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
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
        <div className="p-12 text-center text-[var(--text-secondary)]">Loading sections...</div>
      ) : sections.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          <span className="text-4xl">📑</span>
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mt-3">No Sections Found</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-md mx-auto">
            {courseFilter !== 'all' || termFilter !== 'all'
              ? 'No sections match the current filter criteria.'
              : 'Create sections to open specific course offerings for an upcoming academic term.'}
          </p>
          {isAdmin && (
            <button
              onClick={openCreateModal}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition"
            >
              Add First Section
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] shadow-sm">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border-color)] bg-[var(--bg-elevated)]/50 text-[var(--text-secondary)] font-medium text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4">Section Code</th>
                <th className="py-3.5 px-4">Course</th>
                <th className="py-3.5 px-4">Academic Term</th>
                <th className="py-3.5 px-4">Capacity</th>
                <th className="py-3.5 px-4">Instructors</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)] text-[var(--text-primary)]">
              {sections.map((sec) => (
                <tr key={sec.id} className="hover:bg-[var(--bg-elevated)]/30 transition">
                  <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                      {sec.section_code}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold">{sec.course_code}</span> —{' '}
                    <span className="text-[var(--text-secondary)]">{sec.course_name}</span>
                  </td>
                  <td className="py-3 px-4 text-[var(--text-secondary)]">
                    {sec.term_name || `Term #${sec.academic_term_id}`}
                  </td>
                  <td className="py-3 px-4 text-[var(--text-secondary)]">
                    <span className="font-medium text-[var(--text-primary)]">{sec.capacity}</span> seats
                  </td>
                  <td className="py-3 px-4">
                    {sec.instructors && sec.instructors.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 items-center">
                        {sec.instructors.map((ins) => (
                          <span
                            key={ins.id}
                            className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${
                              ins.is_primary
                                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400 font-semibold'
                                : 'bg-[var(--bg-elevated)] border-[var(--border-color)] text-[var(--text-secondary)]'
                            }`}
                          >
                            <span>👨‍🏫</span>
                            <span>{ins.faculty_name}</span>
                            {ins.is_primary && <span className="text-[9px] text-indigo-300 uppercase">(Lead)</span>}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-[var(--text-muted)] italic">Unassigned</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold capitalize ${
                        sec.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                      }`}
                    >
                      {sec.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    {isAdmin ? (
                      <>
                        <button
                          onClick={() => openInstructorsModal(sec)}
                          className="px-2.5 py-1 text-xs font-medium rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition"
                        >
                          Instructors ({sec.instructors?.length || 0})
                        </button>
                        <button
                          onClick={() => openEditModal(sec)}
                          className="px-2.5 py-1 text-xs font-medium rounded-lg text-indigo-400 hover:bg-indigo-500/10 transition ml-1"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(sec)}
                          className="px-2.5 py-1 text-xs font-medium rounded-lg text-rose-400 hover:bg-rose-500/10 transition ml-1"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => openInstructorsModal(sec)}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition"
                      >
                        View Instructors
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Section Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">
                {editingSection ? 'Edit Section' : 'Create Course Section'}
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
                    Course *
                  </label>
                  <select
                    disabled={Boolean(editingSection)}
                    value={form.course_id}
                    onChange={(e) => setForm({ ...form, course_id: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} — {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Academic Term *
                  </label>
                  <select
                    disabled={Boolean(editingSection)}
                    value={form.academic_term_id}
                    onChange={(e) => setForm({ ...form, academic_term_id: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {terms.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.academic_year})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Section Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SEC-01"
                    value={form.section_code}
                    onChange={(e) => setForm({ ...form, section_code: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] font-mono focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Capacity *
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="5000"
                    required
                    value={form.capacity}
                    onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Status
                  </label>
                  <select
                    value={form.status || 'active'}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="active">Active</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Description / Meeting Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Optional section notes (e.g. Honours cohort, Lab group B)..."
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
                  {submitting ? 'Saving...' : editingSection ? 'Save Changes' : 'Create Section'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manage Instructors Modal */}
      {instructorModalOpen && managingSection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-lg rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3">
              <div>
                <h3 className="text-lg font-bold text-[var(--text-primary)]">
                  Section Instructors
                </h3>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  {managingSection.course_code} — Section {managingSection.section_code}
                </p>
              </div>
              <button
                onClick={() => setInstructorModalOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition text-lg"
              >
                ✕
              </button>
            </div>

            {/* Current Instructors List */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Assigned Faculty
              </h4>
              {managingSection.instructors && managingSection.instructors.length > 0 ? (
                <div className="divide-y divide-[var(--border-subtle)] border border-[var(--border-color)] rounded-xl bg-[var(--bg-primary)] overflow-hidden">
                  {managingSection.instructors.map((ins) => (
                    <div key={ins.id} className="p-3 flex items-center justify-between gap-3 text-sm">
                      <div>
                        <div className="font-semibold text-[var(--text-primary)] flex items-center gap-2">
                          <span>{ins.faculty_name}</span>
                          {ins.is_primary && (
                            <span className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-500/10 text-indigo-400 font-bold border border-indigo-500/20 uppercase">
                              Primary Lead
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-[var(--text-muted)]">
                          {ins.faculty_title || 'Faculty'} • <span className="capitalize">{ins.role.replace('_', ' ')}</span> • {ins.faculty_email}
                        </div>
                      </div>
                      {isAdmin && (
                        <button
                          onClick={() => handleRemoveFaculty(ins.id)}
                          disabled={instructorActionLoading}
                          className="px-2.5 py-1 text-xs font-medium rounded-lg text-rose-400 hover:bg-rose-500/10 transition"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-[var(--text-muted)] border border-dashed border-[var(--border-color)] rounded-xl">
                  No instructors assigned yet.
                </div>
              )}
            </div>

            {/* Assign New Instructor Form (Admin Only) */}
            {isAdmin && (
              <form onSubmit={handleAssignFaculty} className="border-t border-[var(--border-color)] pt-4 space-y-3 text-sm">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Assign New Faculty Member
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                      Faculty Member *
                    </label>
                    <select
                      value={assigningFacultyId}
                      onChange={(e) => setAssigningFacultyId(Number(e.target.value))}
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                    >
                      {facultyList.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.user_name} ({f.title || 'Faculty'})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                      Role
                    </label>
                    <select
                      value={assigningRole}
                      onChange={(e) => setAssigningRole(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="instructor">Instructor</option>
                      <option value="co_instructor">Co-Instructor</option>
                      <option value="teaching_assistant">Teaching Assistant</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="is_primary"
                    checked={assigningPrimary}
                    onChange={(e) => setAssigningPrimary(e.target.checked)}
                    className="rounded border-[var(--border-color)] text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor="is_primary" className="text-xs text-[var(--text-secondary)] select-none">
                    Assign as Primary / Lead Instructor
                  </label>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={instructorActionLoading || !assigningFacultyId}
                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition"
                  >
                    {instructorActionLoading ? 'Assigning...' : 'Assign to Section'}
                  </button>
                </div>
              </form>
            )}

            <div className="flex justify-end pt-3 border-t border-[var(--border-color)]">
              <button
                type="button"
                onClick={() => setInstructorModalOpen(false)}
                className="px-4 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
