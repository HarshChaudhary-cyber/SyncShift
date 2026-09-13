'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useUniversity } from '../layout';
import {
  api,
  Timetable,
  TimetableCreatePayload,
  AcademicTerm,
  getErrorMessage,
} from '@/lib/api';

export default function TimetablesPage() {
  const { institution, isAdmin } = useUniversity();
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedTerm, setSelectedTerm] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  // Create Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<TimetableCreatePayload>({
    academic_term_id: 0,
    name: '',
    description: '',
    status: 'draft',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      setError(null);
      const [ttData, termsData] = await Promise.all([
        api.getTimetables(institution.id, {
          term_id: selectedTerm !== 'all' ? parseInt(selectedTerm, 10) : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
        }),
        api.getAcademicTerms(institution.id),
      ]);
      setTimetables(ttData);
      setTerms(termsData);

      // Pre-select first active or upcoming term in create modal if not set
      if (form.academic_term_id === 0 && termsData.length > 0) {
        const activeTerm = termsData.find((t) => t.status === 'active') || termsData[0];
        setForm((prev) => ({ ...prev, academic_term_id: activeTerm.id }));
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load timetables'));
    } finally {
      setLoading(false);
    }
  }, [institution, selectedTerm, statusFilter, form.academic_term_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredTimetables = useMemo(() => {
    if (!search.trim()) return timetables;
    const s = search.toLowerCase();
    return timetables.filter(
      (t) =>
        t.name.toLowerCase().includes(s) ||
        (t.description && t.description.toLowerCase().includes(s)) ||
        (t.term_name && t.term_name.toLowerCase().includes(s))
    );
  }, [timetables, search]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution) return;
    if (!form.name.trim()) {
      setFormError('Timetable name is required.');
      return;
    }
    if (!form.academic_term_id) {
      setFormError('Please select an academic term.');
      return;
    }

    try {
      setSubmitting(true);
      setFormError(null);
      await api.createTimetable(institution.id, {
        academic_term_id: form.academic_term_id,
        name: form.name.trim(),
        description: form.description?.trim() || undefined,
        status: form.status || 'draft',
      });
      setModalOpen(false);
      setForm({
        academic_term_id: terms[0]?.id || 0,
        name: '',
        description: '',
        status: 'draft',
      });
      await loadData();
    } catch (err: unknown) {
      setFormError(getErrorMessage(err, 'Failed to create timetable'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSetActive = async (timetable: Timetable) => {
    if (!institution || timetable.status === 'active') return;
    try {
      await api.updateTimetable(institution.id, timetable.id, { status: 'active' });
      await loadData();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to activate timetable'));
    }
  };

  const handleArchive = async (timetable: Timetable) => {
    if (!institution || timetable.status === 'archived') return;
    if (!confirm(`Are you sure you want to archive timetable "${timetable.name}"?`)) return;
    try {
      await api.deleteTimetable(institution.id, timetable.id);
      await loadData();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to archive timetable'));
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-[var(--border)]">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">University Timetables</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            See and manage your university&apos;s class schedule. Connect courses, sections, rooms, and faculty into official weekly timetables.
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setFormError(null);
              setModalOpen(true);
            }}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 shrink-0 cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Create Timetable
          </button>
        )}
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs underline hover:opacity-80">
            Dismiss
          </button>
        </div>
      )}

      {/* Filters Toolbar */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter tabs */}
          <div className="inline-flex rounded-lg bg-[var(--surface-hover)] p-0.5 text-xs font-medium text-[var(--text-secondary)]">
            {['all', 'active', 'draft', 'archived'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-md capitalize transition-all cursor-pointer ${
                  statusFilter === st
                    ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-sm font-semibold'
                    : 'hover:text-[var(--text-primary)]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Academic Term Filter */}
          <select
            value={selectedTerm}
            onChange={(e) => setSelectedTerm(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Academic Terms</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.academic_year})
              </option>
            ))}
          </select>
        </div>

        {/* Search input */}
        <div className="relative w-full md:w-64">
          <input
            type="text"
            placeholder="Search timetables..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-[var(--text-tertiary)]"
          />
          <svg
            className="w-4 h-4 absolute left-2.5 top-2 text-[var(--text-tertiary)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Timetables Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-48 rounded-xl border border-[var(--border)] bg-[var(--surface)] animate-pulse" />
          ))}
        </div>
      ) : filteredTimetables.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface)]/50">
          <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-600 mx-auto flex items-center justify-center text-xl mb-3">
            🗓️
          </div>
          <h3 className="text-base font-semibold text-[var(--text-primary)]">No Timetables Found</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
            {search || selectedTerm !== 'all' || statusFilter !== 'all'
              ? 'No timetables match your current filters. Try changing your search or filters.'
              : 'Create the first baseline academic timetable to begin scheduling section meetings.'}
          </p>
          {isAdmin && !search && selectedTerm === 'all' && (
            <button
              onClick={() => setModalOpen(true)}
              className="mt-4 inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm cursor-pointer"
            >
              + Create Timetable
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTimetables.map((tt) => {
            const isActive = tt.status === 'active';
            const isDraft = tt.status === 'draft';
            return (
              <div
                key={tt.id}
                className="flex flex-col justify-between rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 hover:border-blue-500/40 transition-all shadow-sm hover:shadow-md group"
              >
                <div>
                  {/* Top Bar: Term & Status */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="inline-flex items-center text-xs font-medium text-[var(--text-secondary)] bg-[var(--surface-hover)] px-2.5 py-1 rounded-md">
                      📅 {tt.term_name || 'Academic Term'}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border capitalize ${
                        isActive
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                          : isDraft
                          ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
                          : 'bg-slate-500/10 text-slate-500 border-slate-500/20'
                      }`}
                    >
                      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />}
                      {tt.status}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <h2 className="text-lg font-bold text-[var(--text-primary)] group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1">
                    {tt.name}
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-1.5 line-clamp-2 min-h-[32px]">
                    {tt.description || 'Official institutional baseline schedule for this term.'}
                  </p>

                  {/* Statistics */}
                  <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-[var(--border)]">
                    <div className="bg-[var(--surface-hover)] rounded-lg p-2.5 text-center">
                      <div className="text-xl font-bold text-[var(--text-primary)]">{tt.meetings_count || 0}</div>
                      <div className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider font-medium mt-0.5">
                        Meetings
                      </div>
                    </div>
                    <div className="bg-[var(--surface-hover)] rounded-lg p-2.5 text-center">
                      <div className="text-xl font-bold text-[var(--text-primary)]">{tt.sections_count || 0}</div>
                      <div className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider font-medium mt-0.5">
                        Sections
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom Actions */}
                <div className="mt-5 pt-3 border-t border-[var(--border)] flex items-center justify-between gap-2">
                  <Link
                    href={`/university/timetables/${tt.id}`}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    View & Edit Schedule →
                  </Link>

                  {isAdmin && (
                    <div className="flex items-center gap-1.5">
                      {!isActive && (
                        <button
                          onClick={() => handleSetActive(tt)}
                          title="Promote to Active Timetable"
                          className="px-2 py-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10 rounded border border-emerald-500/20 transition-all cursor-pointer"
                        >
                          Set Active
                        </button>
                      )}
                      {tt.status !== 'archived' && (
                        <button
                          onClick={() => handleArchive(tt)}
                          title="Archive timetable"
                          className="p-1 text-[var(--text-tertiary)] hover:text-red-500 hover:bg-red-500/10 rounded transition-all cursor-pointer"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <h3 className="text-lg font-bold text-[var(--text-primary)]">Create Baseline Timetable</h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-xl leading-none cursor-pointer"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Academic Term *</label>
                <select
                  value={form.academic_term_id}
                  onChange={(e) => setForm({ ...form, academic_term_id: parseInt(e.target.value, 10) })}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={0} disabled>
                    Select an Academic Term
                  </option>
                  {terms.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.academic_year}) — {t.status}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Timetable Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Fall 2026 Authoritative Master"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-[var(--text-tertiary)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Notes about this baseline schedule..."
                  value={form.description || ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-[var(--text-tertiary)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Initial Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="draft">Draft (Work in progress)</option>
                  <option value="active">Active (Authoritative for enrolled students)</option>
                </select>
                <p className="text-[11px] text-[var(--text-tertiary)] mt-1">
                  Setting a timetable as Active will automatically promote it as the official schedule for enrolled students.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border)]">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] rounded-lg transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 cursor-pointer"
                >
                  {submitting ? 'Creating...' : 'Create Timetable'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
