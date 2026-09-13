'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import { api, Department, DepartmentCreatePayload } from '@/lib/api';

export default function DepartmentsPage() {
  const { institution, isAdmin } = useUniversity();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [form, setForm] = useState<DepartmentCreatePayload>({
    name: '',
    code: '',
    description: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadDepartments = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDepartments(institution.id);
      setDepartments(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load departments');
    } finally {
      setLoading(false);
    }
  }, [institution]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (!institution) return;
      try {
        setLoading(true);
        setError(null);
        const data = await api.getDepartments(institution.id);
        if (!cancelled) {
          setDepartments(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load departments');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [institution]);

  const openCreateModal = () => {
    setEditingDept(null);
    setForm({ name: '', code: '', description: '' });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (dept: Department) => {
    setEditingDept(dept);
    setForm({ name: dept.name, code: dept.code, description: dept.description || '' });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.code.trim()) {
      setFormError('Department name and code are required.');
      return;
    }

    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingDept) {
        await api.updateDepartment(institution.id, editingDept.id, {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || null,
        });
      } else {
        await api.createDepartment(institution.id, {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || undefined,
        });
      }

      setModalOpen(false);
      await loadDepartments();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Operation failed. Please verify code uniqueness.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (dept: Department) => {
    if (!institution) return;
    if (!confirm(`Are you sure you want to deactivate department "${dept.name}" (${dept.code})?`)) {
      return;
    }
    try {
      await api.deleteDepartment(institution.id, dept.id);
      await loadDepartments();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to deactivate department');
    }
  };

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Departments
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage academic departments, subject faculties, and organizational divisions for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-sm"
          >
            <span>+</span> Add Department
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs text-[var(--text-secondary)]">Loading departments…</p>
        </div>
      ) : departments.length === 0 ? (
        <div className="text-center py-16 rounded-2xl bg-[var(--bg-card)] border border-dashed border-[var(--border-color)]">
          <span className="text-3xl block mb-2">🏢</span>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">No departments yet</h3>
          <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
            {isAdmin
              ? 'Get started by creating your university’s academic departments (e.g. Computer Science, Mathematics).'
              : 'Your institution has not configured departments yet.'}
          </p>
          {isAdmin && (
            <button
              onClick={openCreateModal}
              className="mt-4 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              + Create First Department
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {departments.map((dept) => (
            <div
              key={dept.id}
              className="p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--border-strong)] transition shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="px-2.5 py-0.5 text-xs font-bold rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {dept.code}
                  </span>
                  <span
                    className={`px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase tracking-wider ${
                      dept.is_active
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-zinc-500/10 text-zinc-400'
                    }`}
                  >
                    {dept.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <h2 className="text-base font-bold text-[var(--text-primary)]">
                  {dept.name}
                </h2>

                {dept.description && (
                  <p className="text-xs text-[var(--text-secondary)] mt-2 line-clamp-3">
                    {dept.description}
                  </p>
                )}
              </div>

              {isAdmin && (
                <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-end gap-2 text-xs">
                  <button
                    onClick={() => openEditModal(dept)}
                    className="px-2.5 py-1 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(dept)}
                    className="px-2.5 py-1 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 transition"
                  >
                    Deactivate
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal for Create/Edit */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-[var(--text-primary)] mb-4">
              {editingDept ? 'Edit Department' : 'Add Academic Department'}
            </h3>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Department Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Computer Science"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Department Code <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CS"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase"
                />
                <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block">
                  Must be unique within your institution.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Optional overview or specializations"
                  value={form.description || ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition disabled:opacity-50"
                >
                  {submitting ? 'Saving…' : editingDept ? 'Save Changes' : 'Create Department'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
