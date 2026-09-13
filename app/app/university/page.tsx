'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useUniversity } from './layout';
import {
  api,
  UniversityDashboardData,
  InstitutionCreatePayload,
  Timetable,
} from '@/lib/api';

export default function UniversityDashboardPage() {
  const { status, loading: contextLoading, refresh, institution, isAdmin } = useUniversity();
  const [dashboardData, setDashboardData] = useState<UniversityDashboardData | null>(null);
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Onboarding Form State (for first-time university registration)
  const [form, setForm] = useState<InstitutionCreatePayload>({
    name: '',
    code: '',
    description: '',
    country: '',
    timezone: 'Europe/London',
    email_domain: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!institution) return;
    let cancelled = false;

    async function loadDashboard() {
      try {
        setLoadingData(true);
        setError(null);
        const [dash, ttList] = await Promise.allSettled([
          api.getUniversityDashboard(institution!.id),
          api.getTimetables(institution!.id),
        ]);

        if (!cancelled) {
          if (dash.status === 'fulfilled') {
            setDashboardData(dash.value);
          }
          if (ttList.status === 'fulfilled') {
            setTimetables(ttList.value);
          }
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load university overview data');
        }
      } finally {
        if (!cancelled) {
          setLoadingData(false);
        }
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [institution]);

  const handleOnboardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.code.trim()) {
      setFormError('University name and code are required.');
      return;
    }

    try {
      setSubmitting(true);
      setFormError(null);
      await api.createInstitution({
        ...form,
        code: form.code.trim().toUpperCase(),
      });
      await refresh();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to initialize university. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (contextLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm text-[var(--text-secondary)]">Loading university profile…</p>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // State 1: User has NO institution yet -> Onboarding view
  // ─────────────────────────────────────────────────────────────────────────────
  if (!status?.has_institution) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-500/10 text-3xl mb-4 border border-indigo-500/20">
            🏛️
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)]">
            Set Up Your University
          </h1>
          <p className="text-sm text-indigo-400 font-medium mt-1">
            Build better timetables and understand their impact on students.
          </p>
          <p className="text-xs text-[var(--text-secondary)] mt-2 max-w-lg mx-auto leading-relaxed">
            Register your institution to begin scheduling baseline timetables, managing academic resources,
            and coordinating conflict-free calendars for students and faculty.
          </p>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 sm:p-8 shadow-sm">
          {formError && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {formError}
            </div>
          )}

          <form onSubmit={handleOnboardSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                Institution Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Oxford University / MIT"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                  Institution Code <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OXFORD or MIT"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                  Country
                </label>
                <input
                  type="text"
                  placeholder="e.g. United Kingdom"
                  value={form.country || ''}
                  onChange={(e) => setForm({ ...form, country: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                  Timezone (IANA)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Europe/London"
                  value={form.timezone || 'Europe/London'}
                  onChange={(e) => setForm({ ...form, timezone: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                  Email Domain
                </label>
                <input
                  type="text"
                  placeholder="e.g. ox.ac.uk"
                  value={form.email_domain || ''}
                  onChange={(e) => setForm({ ...form, email_domain: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5">
                Description
              </label>
              <textarea
                rows={3}
                placeholder="Brief institutional description or campus notes"
                value={form.description || ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-4 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-sm disabled:opacity-50 cursor-pointer"
            >
              {submitting ? 'Setting up Institution…' : 'Initialize Institution & Become Admin'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // State 2: User belongs to an institution -> Dashboard view
  // ─────────────────────────────────────────────────────────────────────────────
  const activeTimetable = timetables.find((t) => t.status === 'active') || timetables[0] || null;

  return (
    <div className="space-y-8">
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* 1. Timetable as the Main Centerpiece */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/60 via-purple-950/40 to-slate-900 border border-indigo-500/30 p-6 sm:p-8 shadow-xl">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="text-2xl">🗓️</span>
              <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                Official University Timetable
              </span>
              {activeTimetable?.status === 'active' && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  Active Baseline Schedule
                </span>
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {activeTimetable ? activeTimetable.name : 'University Timetable Schedule'}
            </h1>

            <p className="text-sm text-slate-300 leading-relaxed">
              {activeTimetable
                ? `See and manage your university's official class schedule. Scheduled meetings automatically appear on enrolled students' calendars and enforce room and instructor availability.`
                : `Create your university's baseline timetable to schedule courses, assign rooms, and provide students with their authoritative academic calendar.`}
            </p>

            {/* Quick Metrics Badge Row */}
            {activeTimetable && (
              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-300">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700/80">
                  <span>📅</span> {activeTimetable.term_name || dashboardData?.active_term?.name || 'Academic Term'}
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700/80 font-medium">
                  <span className="text-indigo-400 font-bold">{activeTimetable.meetings_count || 0}</span> Scheduled Classes
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-700/80 font-medium">
                  <span className="text-purple-400 font-bold">{activeTimetable.sections_count || 0}</span> Sections Covered
                </span>
              </div>
            )}
          </div>

          {/* Centerpiece Call to Action Buttons */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            {activeTimetable ? (
              <>
                <Link
                  href={`/university/timetables/${activeTimetable.id}`}
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition shadow-lg shadow-indigo-600/30 cursor-pointer"
                >
                  <span>Open Timetable Grid</span>
                  <span>→</span>
                </Link>
                <Link
                  href="/university/timetables"
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs transition cursor-pointer"
                >
                  <span>All Timetables</span>
                </Link>
              </>
            ) : (
              <Link
                href="/university/timetables"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition shadow-lg shadow-indigo-600/30 cursor-pointer"
              >
                <span>+ Create First Timetable</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 2. Task-Driven Quick Actions Bar */}
      <div className="p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Quick Actions
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Everyday operational tasks for university administrators.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            href="/university/timetables"
            className="flex flex-col items-start p-3.5 rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] hover:border-indigo-500/40 transition group cursor-pointer"
          >
            <span className="text-2xl mb-2">🗓️</span>
            <span className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition">
              View Timetable
            </span>
            <span className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Weekly master grid
            </span>
          </Link>

          <Link
            href={activeTimetable ? `/university/timetables/${activeTimetable.id}` : '/university/timetables'}
            className="flex flex-col items-start p-3.5 rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] hover:border-indigo-500/40 transition group cursor-pointer"
          >
            <span className="text-2xl mb-2">🕒</span>
            <span className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition">
              Add Class Meeting
            </span>
            <span className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Schedule time & room
            </span>
          </Link>

          <Link
            href="/university/resources"
            className="flex flex-col items-start p-3.5 rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] hover:border-indigo-500/40 transition group cursor-pointer"
          >
            <span className="text-2xl mb-2">📚</span>
            <span className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition">
              Academic Resources
            </span>
            <span className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Courses, rooms & staff
            </span>
          </Link>

          <Link
            href="/university/members"
            className="flex flex-col items-start p-3.5 rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] hover:border-indigo-500/40 transition group cursor-pointer"
          >
            <span className="text-2xl mb-2">👥</span>
            <span className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition">
              View Students
            </span>
            <span className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Directory & enrollments
            </span>
          </Link>
        </div>
      </div>

      {/* 3. Streamlined Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Link
          href="/university/terms"
          className="group p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/40 transition shadow-xs flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">📅</span>
              <span className="text-xs font-semibold uppercase text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                Active Term
              </span>
            </div>
            <p className="mt-3 text-lg font-bold text-[var(--text-primary)] truncate">
              {loadingData ? '…' : dashboardData?.active_term?.name || 'No Active Term'}
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {dashboardData?.active_term
                ? `${dashboardData.active_term.academic_year} (${dashboardData.active_term.term_type})`
                : 'Configure instructional periods'}
            </p>
          </div>
          <span className="mt-4 text-xs font-semibold text-indigo-400 group-hover:underline">
            Manage Terms →
          </span>
        </Link>

        <Link
          href="/university/resources"
          className="group p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/40 transition shadow-xs flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">🏛️</span>
              <span className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                Building Blocks
              </span>
            </div>
            <p className="mt-3 text-3xl font-black text-[var(--text-primary)]">
              {loadingData ? '…' : dashboardData?.department_count ?? 0}
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Academic Departments Registered
            </p>
          </div>
          <span className="mt-4 text-xs font-semibold text-indigo-400 group-hover:underline">
            Manage Academic Resources →
          </span>
        </Link>

        <Link
          href="/university/members"
          className="group p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/40 transition shadow-xs flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-2xl">👥</span>
              <span className="text-xs font-semibold uppercase text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">
                Campus Users
              </span>
            </div>
            <p className="mt-3 text-3xl font-black text-[var(--text-primary)]">
              {loadingData ? '…' : dashboardData?.member_count ?? 1}
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Enrolled Students & Faculty
            </p>
          </div>
          <span className="mt-4 text-xs font-semibold text-indigo-400 group-hover:underline">
            Manage Student Directory →
          </span>
        </Link>
      </div>

      {/* 4. Institutional Profile Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xs">
        <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-4">
          Campus Profile
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 text-sm">
          <div>
            <span className="text-xs text-[var(--text-muted)] block">Official Code</span>
            <span className="font-semibold text-[var(--text-primary)]">{institution?.code}</span>
          </div>
          <div>
            <span className="text-xs text-[var(--text-muted)] block">Campus Timezone</span>
            <span className="font-semibold text-[var(--text-primary)]">{institution?.timezone}</span>
          </div>
          <div>
            <span className="text-xs text-[var(--text-muted)] block">Country</span>
            <span className="font-semibold text-[var(--text-primary)]">{institution?.country || 'Global'}</span>
          </div>
          <div>
            <span className="text-xs text-[var(--text-muted)] block">Institutional Email Domain</span>
            <span className="font-semibold text-[var(--text-primary)]">{institution?.email_domain || 'Configured for campus users'}</span>
          </div>
        </div>
        {institution?.description && (
          <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] leading-relaxed">
            {institution.description}
          </div>
        )}
      </div>
    </div>
  );
}
