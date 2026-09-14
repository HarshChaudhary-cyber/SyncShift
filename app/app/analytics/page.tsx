'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, AnalyticsData, UserInstitutionStatus } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import ScheduleHealthCard from '@/components/Analytics/ScheduleHealthCard';
import WorkloadChart from '@/components/Analytics/WorkloadChart';
import TimeDistributionChart from '@/components/Analytics/TimeDistributionChart';
import WeeklyHoursCard from '@/components/Analytics/WeeklyHoursCard';
import EarningsCard from '@/components/Analytics/EarningsCard';
import ImportModal from '@/components/calendar/ImportModal';
import { showSuccessToast } from '@/lib/toast';

function AnalyticsContent() {
  const router = useRouter();
  const { weekStart, goToNextWeek, goToPrevWeek, goToCurrentWeek } = useCalendar();

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [institutionStatus, setInstitutionStatus] = useState<UserInstitutionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const fetchAnalytics = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const [data, inst] = await Promise.allSettled([
        api.getAnalytics(weekStart),
        api.getMyInstitutionStatus(),
      ]);
      if (data.status === 'fulfilled') {
        setAnalytics(data.value);
      } else {
        const err = data.reason;
        if (err?.status === 401) {
          router.replace('/login');
          return;
        }
        setError(err?.message || 'Failed to load schedule analytics');
      }
      if (inst.status === 'fulfilled') {
        setInstitutionStatus(inst.value);
      }
    } catch (err: any) {
      if (err?.status === 401) {
        router.replace('/login');
        return;
      }
      setError(err?.message || 'Failed to load schedule analytics');
    } finally {
      setLoading(false);
    }
  }, [weekStart, router]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const isAdmin =
    institutionStatus?.membership?.role === 'admin' ||
    institutionStatus?.membership?.role === 'super_admin';

  // Week navigation
  const handlePrevWeek = () => {
    goToPrevWeek();
  };

  const handleNextWeek = () => {
    goToNextWeek();
  };

  const handleTodayWeek = () => {
    goToCurrentWeek();
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col">
      <Navbar onImportClick={() => setImportModalOpen(true)} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {isAdmin && (
          <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <span className="text-xl">🏛️</span>
              <div>
                <span className="font-bold text-indigo-300">University Administrator: </span>
                <span className="text-[var(--text-secondary)]">
                  You are viewing personal student schedule analytics. For campus-wide room utilization, section capacity, and timetable impact, access University Insights.
                </span>
              </div>
            </div>
            <Link
              href="/university/insights"
              className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold whitespace-nowrap transition"
            >
              University Insights →
            </Link>
          </div>
        )}

        {/* Page Header & Week Navigator */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-[var(--text-primary)] tracking-tight flex items-center gap-2.5">
              <span>📊</span>
              <span>Schedule Analytics</span>
            </h1>
            <p className="text-xs sm:text-sm text-[var(--text-secondary)] mt-1">
              Deterministic health scoring, workload distribution, and work-hour tracking.
            </p>
          </div>

          {/* Week Selector Controls */}
          <div className="flex items-center gap-2 self-start sm:self-auto bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-1.5 shadow-sm">
            <button
              onClick={handlePrevWeek}
              aria-label="Previous week"
              className="p-1.5 hover:bg-[var(--bg-secondary)] rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
            >
              ◀
            </button>
            <button
              onClick={handleTodayWeek}
              className="px-2.5 py-1 text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--bg-input)] rounded-lg text-[var(--text-primary)] transition cursor-pointer font-mono"
            >
              {analytics?.period ? `${analytics.period.start} – ${analytics.period.end}` : 'Current Week'}
            </button>
            <button
              onClick={handleNextWeek}
              aria-label="Next week"
              className="p-1.5 hover:bg-[var(--bg-secondary)] rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
            >
              ▶
            </button>
          </div>
        </div>

        {/* Error / Retry Banner */}
        {error && !loading && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-between gap-3 text-xs text-rose-700 dark:text-rose-300">
            <span className="font-semibold">Analytics couldn't be loaded.</span>
            <button
              onClick={() => fetchAnalytics(false)}
              className="px-3 py-1.5 bg-rose-600 text-white rounded-lg font-semibold hover:bg-rose-500 transition cursor-pointer shadow-sm"
            >
              Retry
            </button>
          </div>
        )}

        {/* Top 3-Column Section: Schedule Health, Work Utilization, Earnings */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
          <div className="h-full">
            <ScheduleHealthCard
              health={analytics?.health || null}
              loading={loading}
            />
          </div>
          <div className="h-full">
            <WeeklyHoursCard
              workLimit={analytics?.work_limit || null}
              loading={loading}
            />
          </div>
          <div className="h-full md:col-span-2 lg:col-span-1">
            <EarningsCard
              earnings={analytics?.earnings || null}
              loading={loading}
            />
          </div>
        </div>

        {/* Mid Section: Daily Workload Chart & Time Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
          <div className="h-full">
            <WorkloadChart
              dailyWorkload={analytics?.daily_workload || []}
              loading={loading}
            />
          </div>
          <div className="h-full">
            <TimeDistributionChart
              distribution={analytics?.time_distribution || null}
              hours={analytics?.hours || null}
              loading={loading}
            />
          </div>
        </div>

        {/* KPI Quick Summary Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-sm">
            <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider block mb-1">
              📚 Class Hours
            </span>
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {analytics?.hours.class_hours ?? 0}h
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-sm">
            <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block mb-1">
              💼 Work Hours
            </span>
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {analytics?.hours.work_hours ?? 0}h
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-sm">
            <span className="text-[11px] font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider block mb-1">
              📖 Study Hours
            </span>
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {analytics?.hours.study_hours ?? 0}h
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-sm">
            <span className="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider block mb-1">
              ⚡ Total Planned
            </span>
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {analytics?.hours.total_hours ?? 0}h
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-sm col-span-2 sm:col-span-1">
            <span className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider block mb-1">
              ⚠️ Conflicts
            </span>
            <span className="text-xl sm:text-2xl font-black text-[var(--text-primary)] font-mono">
              {analytics?.conflicts.total ?? 0}
            </span>
          </div>
        </div>
      </main>

      <ImportModal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onToast={(msg) => showSuccessToast(msg)}
      />
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <CalendarProvider>
        <AnalyticsContent />
      </CalendarProvider>
    </ProtectedRoute>
  );
}
