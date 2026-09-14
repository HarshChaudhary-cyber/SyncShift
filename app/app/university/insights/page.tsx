'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useUniversity } from '../layout';
import {
  api,
  UniversityDashboardAnalyticsResponse,
  SectionDemandItem,
  RoomUtilizationItem,
  TimetableChangeHistoryItem,
  DepartmentComparisonItem,
} from '@/lib/api';

export default function UniversityInsightsPage() {
  const { institution, isAdmin, loading: contextLoading } = useUniversity();

  const [data, setData] = useState<UniversityDashboardAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states (Progressive Disclosure)
  const [selectedTermId, setSelectedTermId] = useState<number | undefined>(undefined);
  const [selectedDeptId, setSelectedDeptId] = useState<number | undefined>(undefined);
  const [sectionSearch, setSectionSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'demand' | 'rooms' | 'timetable' | 'departments'>('demand');

  const fetchAnalytics = async (termId?: number, deptId?: number) => {
    if (!institution?.id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getUniversityAnalyticsDashboard(institution.id, termId, deptId);
      setData(res);
      // Synchronize selected term if not already explicitly chosen
      if (termId === undefined && res.term_id) {
        setSelectedTermId(res.term_id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load university insights.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (institution?.id) {
      fetchAnalytics(selectedTermId, selectedDeptId);
    }
  }, [institution?.id, selectedTermId, selectedDeptId]);

  // Client-side search filters for sections table
  const filteredSections = useMemo(() => {
    if (!data?.enrollment?.all_sections) return [];
    if (!sectionSearch.trim()) return data.enrollment.all_sections;
    const q = sectionSearch.toLowerCase();
    return data.enrollment.all_sections.filter(
      (s) =>
        s.section_code.toLowerCase().includes(q) ||
        s.course_code.toLowerCase().includes(q) ||
        s.course_title.toLowerCase().includes(q) ||
        (s.department_name && s.department_name.toLowerCase().includes(q))
    );
  }, [data?.enrollment?.all_sections, sectionSearch]);

  if (contextLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm text-[var(--text-secondary)]">Loading university profile…</p>
      </div>
    );
  }

  if (!institution) {
    return (
      <div className="text-center py-16 max-w-lg mx-auto">
        <span className="text-4xl mb-3 block">🏛️</span>
        <h2 className="text-xl font-bold text-[var(--text-primary)]">No University Selected</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-2">
          Please register or select an institution before accessing university insights.
        </p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-16 max-w-lg mx-auto bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8 shadow-sm">
        <span className="text-4xl mb-3 block">🔒</span>
        <h2 className="text-xl font-bold text-[var(--text-primary)]">Administrator Access Required</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-2">
          University-wide insights and operational analytics are reserved for institution administrators.
          Students can review their personal schedule analytics in the student dashboard.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/university"
            className="px-4 py-2 text-sm font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition"
          >
            Return to University Home
          </Link>
          <Link
            href="/analytics"
            className="px-4 py-2 text-sm font-semibold rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] text-[var(--text-primary)] transition"
          >
            Personal Schedule Analytics
          </Link>
        </div>
      </div>
    );
  }

  const overview = data?.overview;
  const enrollment = data?.enrollment;
  const rooms = data?.rooms;
  const timetableHealth = data?.timetable;
  const departments = data?.departments || [];

  return (
    <div className="space-y-8 pb-16">
      {/* 1. Header & Context */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border-color)] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📊</span>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)]">
              University Insights
            </h1>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-1.5 max-w-2xl">
            Understand timetable usage, student impact, and university scheduling patterns based on real operational data.
          </p>
        </div>

        {/* Freshness Badge & Refresh */}
        <div className="flex items-center gap-3 self-start md:self-auto">
          {data?.data_freshness_label && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              {data.data_freshness_label}
            </span>
          )}
          <button
            onClick={() => fetchAnalytics(selectedTermId, selectedDeptId)}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-[var(--bg-secondary)] hover:bg-[var(--bg-hover)] border border-[var(--border-color)] text-xs font-medium text-[var(--text-primary)] transition disabled:opacity-50 cursor-pointer"
            title="Refresh current analytics data"
          >
            {loading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {/* 2. Progressive Filter Bar */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 sm:p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Academic Term Filter */}
            <div>
              <label htmlFor="term-select" className="block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1">
                Academic Term
              </label>
              <select
                id="term-select"
                value={selectedTermId ?? data?.term_id ?? ''}
                onChange={(e) => setSelectedTermId(e.target.value ? Number(e.target.value) : undefined)}
                className="px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs font-medium text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
              >
                {data?.available_terms?.map((term) => (
                  <option key={term.id} value={term.id}>
                    {term.name} ({term.code}) {term.status === 'active' ? '• Active' : ''}
                  </option>
                ))}
                {(!data?.available_terms || data.available_terms.length === 0) && (
                  <option value="">No terms configured</option>
                )}
              </select>
            </div>

            {/* Department Filter */}
            <div>
              <label htmlFor="dept-select" className="block text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1">
                Department
              </label>
              <select
                id="dept-select"
                value={selectedDeptId ?? ''}
                onChange={(e) => setSelectedDeptId(e.target.value ? Number(e.target.value) : undefined)}
                className="px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs font-medium text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500 min-w-[180px]"
              >
                <option value="">All Departments</option>
                {departments.map((dept) => (
                  <option key={dept.department_id} value={dept.department_id}>
                    {dept.department_name} ({dept.department_code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Assistant Quick Helper Prompt */}
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] px-3 py-2 rounded-xl border border-[var(--border-color)]">
            <span>💡</span>
            <span>Tip: Ask SyncShift can answer ad-hoc questions like <em>&quot;Which rooms are most used?&quot;</em></span>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => fetchAnalytics(selectedTermId, selectedDeptId)}
            className="text-xs underline hover:text-red-300 ml-4 font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {/* 3. Summary KPI Cards ("What should I know right now?") */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Students */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">👥</span>
            <span className="text-[10px] font-bold uppercase text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">
              Students
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : overview?.enrolled_students ?? 0}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Enrolled in sections ({overview?.active_students ?? 0} total)
            </p>
          </div>
        </div>

        {/* Active Sections */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">📚</span>
            <span className="text-[10px] font-bold uppercase text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
              Sections
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : overview?.active_sections ?? 0}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Across {overview?.active_courses ?? 0} courses
            </p>
          </div>
        </div>

        {/* Scheduled Classes */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">🗓️</span>
            <span className="text-[10px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              Meetings
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : overview?.scheduled_classes ?? 0}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Scheduled classes ({overview?.unscheduled_sections ?? 0} unscheduled)
            </p>
          </div>
        </div>

        {/* Room Scheduled Utilization */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">🏫</span>
            <span className="text-[10px] font-bold uppercase text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
              Room Usage
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : `${overview?.scheduled_room_utilization_rate ?? 0}%`}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Scheduled utilization ({overview?.active_rooms ?? 0} rooms)
            </p>
          </div>
        </div>

        {/* Conflicts */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">⚠️</span>
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                (overview?.timetable_conflicts ?? 0) > 0
                  ? 'text-rose-400 bg-rose-500/10'
                  : 'text-emerald-400 bg-emerald-500/10'
              }`}
            >
              Conflicts
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : overview?.timetable_conflicts ?? 0}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              {(overview?.timetable_conflicts ?? 0) === 0 ? 'All conflict-free' : 'Collisions detected'}
            </p>
          </div>
        </div>

        {/* Impact */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xl">📢</span>
            <span className="text-[10px] font-bold uppercase text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">
              Impact
            </span>
          </div>
          <div className="mt-2.5">
            <div className="text-2xl font-black text-[var(--text-primary)]">
              {loading ? '…' : overview?.students_affected_by_changes ?? 0}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Students notified in {overview?.recent_timetable_changes ?? 0} changes
            </p>
          </div>
        </div>
      </div>

      {/* 4. Actionable Alerts Bar */}
      {enrollment && enrollment.high_demand_sections.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚡</span>
            <div>
              <p className="text-sm font-bold text-amber-300">
                {enrollment.high_demand_sections.length}{' '}
                {enrollment.high_demand_sections.length === 1 ? 'section is' : 'sections are'} nearing capacity (&ge;90%)
              </p>
              <p className="text-xs text-amber-400/80 mt-0.5">
                Consider opening additional section seats or adjusting classroom assignments.
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setActiveTab('demand');
              setSectionSearch(enrollment.high_demand_sections[0]?.section_code || '');
            }}
            className="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-semibold transition cursor-pointer self-end sm:self-auto"
          >
            Inspect High Demand →
          </button>
        </div>
      )}

      {timetableHealth && timetableHealth.conflicts.total_conflicts > 0 && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <p className="text-sm font-bold text-rose-300">
                {timetableHealth.conflicts.total_conflicts} scheduling conflicts require attention
              </p>
              <p className="text-xs text-rose-400/80 mt-0.5">
                {timetableHealth.conflicts.room_collisions} room collisions,{' '}
                {timetableHealth.conflicts.faculty_collisions} faculty collisions,{' '}
                {timetableHealth.conflicts.student_class_collisions} student class clashes.
              </p>
            </div>
          </div>
          <Link
            href="/university/timetables"
            className="px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold transition cursor-pointer self-end sm:self-auto"
          >
            Open Timetable Editor →
          </Link>
        </div>
      )}

      {/* 5. Navigation Subtabs */}
      <div className="border-b border-[var(--border-color)]">
        <nav className="flex space-x-6 overflow-x-auto pb-px" aria-label="Insights Tabs">
          <button
            onClick={() => setActiveTab('demand')}
            className={`pb-3 text-sm font-bold border-b-2 transition whitespace-nowrap cursor-pointer ${
              activeTab === 'demand'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            📋 Enrollment & Section Demand
          </button>
          <button
            onClick={() => setActiveTab('rooms')}
            className={`pb-3 text-sm font-bold border-b-2 transition whitespace-nowrap cursor-pointer ${
              activeTab === 'rooms'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            🏫 Room Scheduled Utilization
          </button>
          <button
            onClick={() => setActiveTab('timetable')}
            className={`pb-3 text-sm font-bold border-b-2 transition whitespace-nowrap cursor-pointer ${
              activeTab === 'timetable'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            🩺 Timetable Health & Impact
          </button>
          <button
            onClick={() => setActiveTab('departments')}
            className={`pb-3 text-sm font-bold border-b-2 transition whitespace-nowrap cursor-pointer ${
              activeTab === 'departments'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            🏛️ Department Comparison
          </button>
        </nav>
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────────
          TAB 1: Enrollment & Section Demand
          ───────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'demand' && (
        <div className="space-y-6">
          {/* Summary Row */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-[var(--text-secondary)] uppercase font-semibold">Total Capacity</span>
              <p className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                {enrollment?.total_capacity ?? 0} seats
              </p>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-[var(--text-secondary)] uppercase font-semibold">Seats Filled</span>
              <p className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                {enrollment?.total_seats_filled ?? 0} ({enrollment?.average_section_utilization ?? 0}%)
              </p>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-amber-400 uppercase font-semibold">High Demand (&ge;90%)</span>
              <p className="text-2xl font-bold text-amber-300 mt-1">
                {enrollment?.high_demand_sections?.length ?? 0} sections
              </p>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-blue-400 uppercase font-semibold">Low Utilization (&le;30%)</span>
              <p className="text-2xl font-bold text-blue-300 mt-1">
                {enrollment?.low_utilization_sections?.length ?? 0} sections
              </p>
            </div>
          </div>

          {/* High Demand Spotlight */}
          {enrollment && enrollment.high_demand_sections.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-amber-500/30 rounded-2xl p-5 shadow-xs">
              <h3 className="text-sm font-bold text-amber-300 flex items-center gap-2 mb-3">
                <span>🔥</span> Sections Nearing Full Capacity
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {enrollment.high_demand_sections.map((sec) => (
                  <div
                    key={sec.section_id}
                    className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-[var(--text-primary)]">
                          {sec.course_code} - {sec.section_code}
                        </span>
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
                          {sec.utilization_rate}% full
                        </span>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 truncate">{sec.course_title}</p>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-muted)]">
                      <span>{sec.enrolled_count} / {sec.capacity} enrolled</span>
                      <span className="font-semibold text-amber-400">{sec.remaining_seats} seats left</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Sections Table */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-[var(--text-primary)]">Section Capacity & Demand</h3>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  Detailed enrollment and remaining seat metrics for active course sections.
                </p>
              </div>
              <input
                type="text"
                placeholder="Search course, section or dept…"
                value={sectionSearch}
                onChange={(e) => setSectionSearch(e.target.value)}
                className="w-full sm:w-64 px-3 py-1.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {filteredSections.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-[var(--border-color)] rounded-xl">
                <span className="text-3xl block mb-2">📚</span>
                <p className="text-sm font-semibold text-[var(--text-primary)]">No sections found</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
                  {sectionSearch
                    ? 'No sections matched your search criteria.'
                    : 'No course sections are registered for this term yet.'}
                </p>
                <Link
                  href="/university/resources"
                  className="inline-block mt-3 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                >
                  Manage Academic Resources →
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)] font-semibold">
                      <th className="py-2.5 px-3">Course / Section</th>
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3 text-right">Enrolled</th>
                      <th className="py-2.5 px-3 text-right">Capacity</th>
                      <th className="py-2.5 px-3 text-right">Remaining</th>
                      <th className="py-2.5 px-3">Utilization</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-color)]">
                    {filteredSections.map((sec) => (
                      <tr key={sec.section_id} className="hover:bg-[var(--bg-secondary)]/50 transition">
                        <td className="py-2.5 px-3">
                          <span className="font-mono font-bold text-[var(--text-primary)]">
                            {sec.course_code} - {sec.section_code}
                          </span>
                          <span className="block text-[11px] text-[var(--text-secondary)] truncate max-w-xs">
                            {sec.course_title}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                          {sec.department_name || '—'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-[var(--text-primary)]">
                          {sec.enrolled_count}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">
                          {sec.capacity}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-[var(--text-primary)]">
                          {sec.remaining_seats}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2 min-w-[120px]">
                            <div className="w-16 h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  sec.utilization_rate >= 90
                                    ? 'bg-amber-400'
                                    : sec.utilization_rate <= 30
                                    ? 'bg-blue-400'
                                    : 'bg-emerald-400'
                                }`}
                                style={{ width: `${Math.min(100, sec.utilization_rate)}%` }}
                              />
                            </div>
                            <span
                              className={`text-[11px] font-semibold ${
                                sec.utilization_rate >= 90
                                  ? 'text-amber-400'
                                  : sec.utilization_rate <= 30
                                  ? 'text-blue-400'
                                  : 'text-[var(--text-primary)]'
                              }`}
                            >
                              {sec.utilization_rate}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <Link
                            href="/university/timetables"
                            className="text-indigo-400 hover:underline text-[11px] font-semibold"
                          >
                            Schedule →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────────
          TAB 2: Room Scheduled Utilization
          ───────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'rooms' && (
        <div className="space-y-6">
          {/* Honest Notice */}
          <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 text-xs text-indigo-300 flex items-start gap-3">
            <span className="text-lg">ℹ️</span>
            <div>
              <p className="font-semibold">Scheduled Room Utilization</p>
              <p className="mt-0.5 text-indigo-400/90 leading-relaxed">
                {rooms?.utilization_label_notice ||
                  'Utilization rates are computed from active scheduled timetable meetings against a standard 45-hour operating week (Mon–Fri, 8 AM–5 PM). They reflect timetable reservations, not physical occupancy.'}
              </p>
            </div>
          </div>

          {/* Summary Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-[var(--text-secondary)] uppercase font-semibold">Total Classrooms</span>
              <p className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                {rooms?.total_rooms ?? 0} rooms
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-1">{rooms?.used_rooms ?? 0} with scheduled meetings</p>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-[var(--text-secondary)] uppercase font-semibold">Overall Scheduled Rate</span>
              <p className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                {rooms?.overall_scheduled_utilization_rate ?? 0}%
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Across all registered institutional rooms</p>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 shadow-xs">
              <span className="text-xs text-[var(--text-secondary)] uppercase font-semibold">Operating Baseline</span>
              <p className="text-2xl font-bold text-[var(--text-primary)] mt-1">
                {rooms?.operating_hours_baseline_per_room ?? 45} hrs / wk
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-1">Standard 5-day instructional operating week</p>
            </div>
          </div>

          {/* Daily Schedule Distribution */}
          {rooms && rooms.daily_utilization.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
              <h3 className="text-base font-bold text-[var(--text-primary)]">Scheduled Hours by Day of Week</h3>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {rooms.daily_utilization.map((day) => (
                  <div key={day.day_of_week} className="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                    <span className="text-xs font-bold text-[var(--text-primary)]">{day.day_name}</span>
                    <div className="mt-2 text-xl font-extrabold text-indigo-400">
                      {day.total_scheduled_hours} hrs
                    </div>
                    <span className="text-[11px] text-[var(--text-secondary)] block mt-0.5">
                      {day.meeting_count} {day.meeting_count === 1 ? 'class meeting' : 'class meetings'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Rooms Table */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)]">Classroom Scheduled Utilization</h3>
            {(!rooms?.all_rooms || rooms.all_rooms.length === 0) ? (
              <div className="text-center py-12 border border-dashed border-[var(--border-color)] rounded-xl">
                <span className="text-3xl block mb-2">🏫</span>
                <p className="text-sm font-semibold text-[var(--text-primary)]">No room utilization data yet</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
                  Add rooms and timetable meetings to track classroom scheduled hours and utilization.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)] font-semibold">
                      <th className="py-2.5 px-3">Room</th>
                      <th className="py-2.5 px-3">Building</th>
                      <th className="py-2.5 px-3 text-right">Capacity</th>
                      <th className="py-2.5 px-3 text-right">Scheduled Hours</th>
                      <th className="py-2.5 px-3 text-right">Meetings</th>
                      <th className="py-2.5 px-3">Scheduled Utilization</th>
                      <th className="py-2.5 px-3">Category</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-color)]">
                    {rooms.all_rooms.map((rm) => (
                      <tr key={rm.room_id} className="hover:bg-[var(--bg-secondary)]/50 transition">
                        <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">
                          {rm.room_name}
                        </td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                          {rm.building || 'Main Campus'}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">
                          {rm.capacity}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-[var(--text-primary)]">
                          {rm.scheduled_hours} hrs
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">
                          {rm.scheduled_meetings_count}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2 min-w-[120px]">
                            <div className="w-16 h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  rm.scheduled_utilization_rate >= 70
                                    ? 'bg-emerald-400'
                                    : rm.scheduled_utilization_rate >= 30
                                    ? 'bg-blue-400'
                                    : 'bg-slate-400'
                                }`}
                                style={{ width: `${Math.min(100, rm.scheduled_utilization_rate)}%` }}
                              />
                            </div>
                            <span className="font-mono text-[11px] font-semibold text-[var(--text-primary)]">
                              {rm.scheduled_utilization_rate}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              rm.utilization_category === 'high'
                                ? 'bg-emerald-500/10 text-emerald-300'
                                : rm.utilization_category === 'balanced'
                                ? 'bg-blue-500/10 text-blue-300'
                                : 'bg-slate-500/10 text-slate-300'
                            }`}
                          >
                            {rm.utilization_category}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────────
          TAB 3: Timetable Health & Impact
          ───────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'timetable' && (
        <div className="space-y-6">
          {/* Active Timetable Banner */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">🗓️</span>
                <h3 className="text-base font-bold text-[var(--text-primary)]">
                  {timetableHealth?.timetable_name || 'Current Term Timetable'}
                </h3>
                <span
                  className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                    timetableHealth?.is_published
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-amber-500/10 text-amber-400'
                  }`}
                >
                  {timetableHealth?.is_published ? 'Published Baseline' : 'Draft Schedule'}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                Active timetable health and student impact monitoring for {data?.term_name}.
              </p>
            </div>
            <Link
              href="/university/timetables"
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
            >
              Open Timetable Editor →
            </Link>
          </div>

          {/* Conflict Category Breakdown */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)]">Conflict Detection Breakdown</h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                <span className="text-xs font-semibold text-[var(--text-secondary)] uppercase">Room Collisions</span>
                <p className="text-2xl font-black text-rose-400 mt-1">
                  {timetableHealth?.conflicts.room_collisions ?? 0}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Rooms booked for multiple classes at once</p>
              </div>

              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                <span className="text-xs font-semibold text-[var(--text-secondary)] uppercase">Faculty Collisions</span>
                <p className="text-2xl font-black text-amber-400 mt-1">
                  {timetableHealth?.conflicts.faculty_collisions ?? 0}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Instructors with overlapping teaching slots</p>
              </div>

              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                <span className="text-xs font-semibold text-[var(--text-secondary)] uppercase">Class Clashes</span>
                <p className="text-2xl font-black text-purple-400 mt-1">
                  {timetableHealth?.conflicts.student_class_collisions ?? 0}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Students enrolled in overlapping courses</p>
              </div>

              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                <span className="text-xs font-semibold text-[var(--text-secondary)] uppercase">Work Shift Clashes</span>
                <p className="text-2xl font-black text-blue-400 mt-1">
                  {timetableHealth?.conflicts.student_work_collisions ?? 0}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Aggregated student personal shift overlaps</p>
              </div>
            </div>
          </div>

          {/* Timetable Version & Impact History */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)]">Publication & Student Impact History</h3>
            <p className="text-xs text-[var(--text-secondary)] -mt-2">
              Audited historical record of published timetable revisions and student notification broadcasts.
            </p>

            {(!timetableHealth?.recent_versions || timetableHealth.recent_versions.length === 0) ? (
              <div className="text-center py-10 border border-dashed border-[var(--border-color)] rounded-xl">
                <span className="text-3xl block mb-2">📜</span>
                <p className="text-sm font-semibold text-[var(--text-primary)]">No published timetable versions yet</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
                  When timetable changes are reviewed and published, student impact metrics and notification summaries will be displayed here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)] font-semibold">
                      <th className="py-2.5 px-3">Version</th>
                      <th className="py-2.5 px-3">Published At</th>
                      <th className="py-2.5 px-3 text-right">Changes Applied</th>
                      <th className="py-2.5 px-3 text-right">Students Affected</th>
                      <th className="py-2.5 px-3 text-right">Notifications Sent</th>
                      <th className="py-2.5 px-3">Broadcast Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-color)]">
                    {timetableHealth.recent_versions.map((ver) => (
                      <tr key={ver.version_id} className="hover:bg-[var(--bg-secondary)]/50 transition">
                        <td className="py-2.5 px-3 font-mono font-bold text-[var(--text-primary)]">
                          v{ver.version_number} {ver.version_name ? `(${ver.version_name})` : ''}
                        </td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                          {ver.published_at ? new Date(ver.published_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-[var(--text-primary)]">
                          {ver.changes_count}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-purple-400">
                          {ver.affected_students}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-indigo-400">
                          {ver.notifications_generated}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-300">
                            {ver.summary_status || 'Delivered'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────────
          TAB 4: Department Comparison
          ───────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'departments' && (
        <div className="space-y-6">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-xs space-y-4">
            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Department Operational Comparison</h3>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                Neutral comparison of course offerings, section capacity pressure, and scheduled teaching hours across departments.
              </p>
            </div>

            {departments.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-[var(--border-color)] rounded-xl">
                <span className="text-3xl block mb-2">🏛️</span>
                <p className="text-sm font-semibold text-[var(--text-primary)]">No departments registered yet</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
                  Create academic departments to track institutional resources by division.
                </p>
                <Link
                  href="/university/resources"
                  className="inline-block mt-3 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                >
                  Create Department →
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)] font-semibold">
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3">Code</th>
                      <th className="py-2.5 px-3 text-right">Courses</th>
                      <th className="py-2.5 px-3 text-right">Sections</th>
                      <th className="py-2.5 px-3 text-right">Capacity</th>
                      <th className="py-2.5 px-3 text-right">Enrolled</th>
                      <th className="py-2.5 px-3">Seat Utilization</th>
                      <th className="py-2.5 px-3 text-right">Scheduled Hours</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-color)]">
                    {departments.map((d) => (
                      <tr key={d.department_id} className="hover:bg-[var(--bg-secondary)]/50 transition">
                        <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">
                          {d.department_name}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[var(--text-secondary)]">
                          {d.department_code}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-primary)] font-medium">
                          {d.courses_count}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-primary)] font-medium">
                          {d.sections_count}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-secondary)]">
                          {d.total_capacity}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[var(--text-primary)] font-semibold">
                          {d.total_enrolled}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2 min-w-[110px]">
                            <div className="w-16 h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full bg-indigo-400"
                                style={{ width: `${Math.min(100, d.average_utilization_rate)}%` }}
                              />
                            </div>
                            <span className="font-mono text-[11px] font-semibold text-[var(--text-primary)]">
                              {d.average_utilization_rate}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-[var(--text-primary)]">
                          {d.scheduled_hours} hrs
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. AI Assistant Prompt Card */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-900/30 via-purple-900/20 to-slate-900/40 border border-indigo-500/20 p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">✨</span>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Ask SyncShift Analytics Assistant</h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-xl">
              SyncShift AI queries deterministic backend analytics tools directly. Ask questions about room bottlenecks, section capacity spikes, or student timetable impact.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-[11px] px-2.5 py-1 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                &quot;Which rooms are most used?&quot;
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                &quot;Which sections are nearly full?&quot;
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                &quot;How many students were affected by the latest timetable update?&quot;
              </span>
            </div>
          </div>
          <Link
            href="/assistant"
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shrink-0 shadow-xs"
          >
            Ask SyncShift →
          </Link>
        </div>
      </div>
    </div>
  );
}
