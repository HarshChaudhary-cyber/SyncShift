'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import CustomSelect from '@/components/ui/CustomSelect';
import { api, AcademicTerm, AcademicTermCreatePayload } from '@/lib/api';

export default function AcademicTermsPage() {
  const { institution, isAdmin } = useUniversity();
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTerm, setEditingTerm] = useState<AcademicTerm | null>(null);
  const [form, setForm] = useState<AcademicTermCreatePayload>({
    name: '',
    academic_year: '2026-2027',
    term_type: 'semester',
    start_date: '',
    end_date: '',
    status: 'upcoming',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadTerms = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAcademicTerms(institution.id);
      setTerms(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load academic terms');
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
        const data = await api.getAcademicTerms(institution.id);
        if (!cancelled) {
          setTerms(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load academic terms');
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
    setEditingTerm(null);
    setForm({
      name: '',
      academic_year: '2026-2027',
      term_type: 'semester',
      start_date: '',
      end_date: '',
      status: 'upcoming',
    });
    setFormError(null);
    setModalOpen(true);
  };

  const openEditModal = (term: AcademicTerm) => {
    setEditingTerm(term);
    setForm({
      name: term.name,
      academic_year: term.academic_year,
      term_type: term.term_type,
      start_date: term.start_date,
      end_date: term.end_date,
      status: term.status,
    });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.academic_year.trim() || !form.start_date || !form.end_date) {
      setFormError('All fields are required.');
      return;
    }

    if (new Date(form.end_date) <= new Date(form.start_date)) {
      setFormError('End date must be strictly after start date.');
      return;
    }

    if (!institution) return;

    try {
      setSubmitting(true);
      setFormError(null);

      if (editingTerm) {
        await api.updateAcademicTerm(institution.id, editingTerm.id, {
          name: form.name.trim(),
          academic_year: form.academic_year.trim(),
          term_type: form.term_type,
          start_date: form.start_date,
          end_date: form.end_date,
          status: form.status,
        });
      } else {
        await api.createAcademicTerm(institution.id, {
          name: form.name.trim(),
          academic_year: form.academic_year.trim(),
          term_type: form.term_type,
          start_date: form.start_date,
          end_date: form.end_date,
          status: form.status,
        });
      }

      setModalOpen(false);
      await loadTerms();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to save academic term.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (term: AcademicTerm) => {
    if (!institution) return;
    if (!confirm(`Are you sure you want to archive academic term "${term.name}"?`)) {
      return;
    }
    try {
      await api.deleteAcademicTerm(institution.id, term.id);
      await loadTerms();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to archive term');
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'upcoming':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'completed':
        return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30';
      default:
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Academic Terms
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Manage institutional semesters, quarters, and active scheduling dates for your university timetable.
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-sm"
          >
            <span>+</span> Add Academic Term
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
          <p className="text-xs text-[var(--text-secondary)]">Loading academic terms…</p>
        </div>
      ) : terms.length === 0 ? (
        <div className="text-center py-16 rounded-2xl bg-[var(--bg-card)] border border-dashed border-[var(--border-color)]">
          <span className="text-3xl block mb-2">📅</span>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">No academic terms yet</h3>
          <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
            {isAdmin
              ? 'Configure your university’s first semester or trimester period.'
              : 'No academic terms have been published yet.'}
          </p>
          {isAdmin && (
            <button
              onClick={openCreateModal}
              className="mt-4 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              + Create First Term
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {terms.map((term) => (
            <div
              key={term.id}
              className="p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[var(--border-strong)] transition shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="px-2.5 py-0.5 text-xs font-semibold rounded-lg bg-[var(--bg-elevated)] text-[var(--text-secondary)] border border-[var(--border-color)] uppercase">
                    {term.term_type}
                  </span>
                  <span
                    className={`px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase tracking-wider border ${getStatusBadgeClass(
                      term.status
                    )}`}
                  >
                    {term.status}
                  </span>
                </div>

                <h2 className="text-base font-bold text-[var(--text-primary)]">
                  {term.name}
                </h2>
                <p className="text-xs font-medium text-[var(--text-secondary)] mt-0.5">
                  Academic Year: {term.academic_year}
                </p>

                <div className="mt-4 p-3 rounded-xl bg-[var(--bg-input)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[var(--text-muted)]">Starts:</span>
                    <span className="font-semibold text-[var(--text-primary)]">{term.start_date}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--text-muted)]">Ends:</span>
                    <span className="font-semibold text-[var(--text-primary)]">{term.end_date}</span>
                  </div>
                </div>
              </div>

              {isAdmin && (
                <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-end gap-2 text-xs">
                  <button
                    onClick={() => openEditModal(term)}
                    className="px-2.5 py-1 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(term)}
                    className="px-2.5 py-1 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 transition"
                  >
                    Archive
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
              {editingTerm ? 'Edit Academic Term' : 'Add Academic Term'}
            </h3>

            {formError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Term Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Fall 2026 Semester"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                    Academic Year <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 2026-2027"
                    value={form.academic_year}
                    onChange={(e) => setForm({ ...form, academic_year: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                    Term Structure
                  </label>
                  <CustomSelect
                    options={[
                      { value: 'semester', label: 'Semester' },
                      { value: 'trimester', label: 'Trimester' },
                      { value: 'quarter', label: 'Quarter' },
                      { value: 'custom', label: 'Custom' },
                    ]}
                    value={form.term_type}
                    onChange={(val) => setForm({ ...form, term_type: String(val) })}
                    portalTheme="university"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                    Start Date <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                    End Date <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={form.end_date}
                    onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[var(--text-secondary)] mb-1">
                  Status
                </label>
                <CustomSelect
                  options={[
                    { value: 'upcoming', label: 'Upcoming' },
                    { value: 'active', label: 'Active (Current)' },
                    { value: 'draft', label: 'Draft' },
                    { value: 'completed', label: 'Completed' },
                    { value: 'archived', label: 'Archived' },
                  ]}
                  value={form.status}
                  onChange={(val) => setForm({ ...form, status: String(val) })}
                  portalTheme="university"
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
                  {submitting ? 'Saving…' : editingTerm ? 'Save Changes' : 'Create Term'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
