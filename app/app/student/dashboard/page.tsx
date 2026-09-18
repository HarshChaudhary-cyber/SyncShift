'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError, DashboardData, StudyTask } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { CalendarProvider } from '@/context/CalendarContext';
import GreetingHeader from '@/components/dashboard/GreetingHeader';
import NextUpCard from '@/components/dashboard/NextUpCard';
import TodayTimeline from '@/components/dashboard/TodayTimeline';
import WeekSummaryCard from '@/components/dashboard/WeekSummaryCard';
import AlertsBanner from '@/components/dashboard/AlertsBanner';
import AdaptiveBanner from '@/components/dashboard/AdaptiveBanner';
import ScheduleHealthCard from '@/components/dashboard/ScheduleHealthCard';
import WorkStudyCard from '@/components/dashboard/WorkStudyCard';
import RecommendationsCard from '@/components/dashboard/RecommendationsCard';
import QuickActions from '@/components/dashboard/QuickActions';
import AcademicSummaryCard from '@/components/dashboard/AcademicSummaryCard';
import BlockModal from '@/components/calendar/BlockModal';
import ImportModal from '@/components/calendar/ImportModal';
import AddTaskModal from '@/components/planner/AddTaskModal';
import { showSuccessToast } from '@/lib/toast';

function StudentDashboardContent() {
  const router = useRouter();
  const { status, user } = useAuthContext();

  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [blockModalState, setBlockModalState] = useState<{
    isOpen: boolean;
    defaultType?: 'class' | 'shift';
  }>({ isOpen: false });

  const [importModalOpen, setImportModalOpen] = useState(false);
  const [addTaskOpen, setAddTaskOpen] = useState(false);

  // Fetch Dashboard Data from GET /api/v1/dashboard
  const fetchDashboard = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const data = await api.getDashboard();
      setDashboardData(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          router.replace('/login');
          return;
        }
        setError(err.message || 'Failed to load dashboard data');
      } else {
        setError("Couldn't load dashboard. Check your connection.");
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  // 1. Fetch on mount
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // 2. Auto-refresh every 5 minutes & on tab visibilitychange
  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchDashboard(true);
    }, 5 * 60 * 1000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboard(true);
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchDashboard]);

  // Modal handlers
  const handleOpenAddClass = () => {
    setBlockModalState({ isOpen: true, defaultType: 'class' });
  };

  const handleOpenAddShift = () => {
    setBlockModalState({ isOpen: true, defaultType: 'shift' });
  };

  const handleOpenAddStudyTask = () => {
    setAddTaskOpen(true);
  };

  const handleOpenImport = () => {
    setImportModalOpen(true);
  };

  const handleCloseBlockModal = () => {
    setBlockModalState({ isOpen: false });
    fetchDashboard(true);
  };

  const handleCloseImportModal = () => {
    setImportModalOpen(false);
    fetchDashboard(true);
  };

  // Auth loading state
  if (status === 'checking') {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading your student dashboard…</p>
        </div>
      </div>
    );
  }

  // Network / server error state with Retry button
  if (error && !dashboardData && !loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="max-w-md w-full text-center bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8 shadow-2xl space-y-4">
          <div className="text-5xl">📡</div>
          <h2 className="text-xl font-bold text-[var(--text-primary)]">
            Couldn&apos;t load student dashboard
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">
            {error || 'Check your connection and try again.'}
          </p>
          <button
            onClick={() => fetchDashboard(false)}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition cursor-pointer shadow-lg shadow-indigo-900/40"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const currency = dashboardData?.user?.currency || '₹';

  return (
    <div className="space-y-6">
      {/* 1. Greeting Header */}
      <GreetingHeader
        user={dashboardData?.user || (user as any)}
        currentDate={dashboardData?.today?.date}
      />

      {/* 1b. Adaptive Guidance */}
      <AdaptiveBanner
        adaptiveState={dashboardData?.adaptive_state}
        onImportClick={handleOpenImport}
        onAddShiftClick={handleOpenAddShift}
      />

      {/* 2. Immediate Attention (conflicts, limit alerts) */}
      <AlertsBanner
        alerts={dashboardData?.alerts || []}
        conflicts={
          dashboardData?.analytics
            ? {
                hard: dashboardData.analytics.conflicts,
                warning: 0,
                total: dashboardData.analytics.conflicts,
              }
            : null
        }
        work={dashboardData?.work || null}
        adaptiveState={dashboardData?.adaptive_state}
      />

      {/* 3 & 4. Primary Grid: Next Event + Today's Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        <div className="h-full">
          <NextUpCard
            nextUp={dashboardData?.next_up || null}
            loading={loading && !dashboardData}
          />
        </div>

        <div className="h-full">
          <TodayTimeline
            today={dashboardData?.today || null}
            currency={currency}
            loading={loading && !dashboardData}
          />
        </div>
      </div>

      {/* 4b. Student Academic Summary */}
      {dashboardData?.academics && (
        <AcademicSummaryCard
          academics={dashboardData.academics}
          loading={loading && !dashboardData}
        />
      )}

      {/* 5 & 6. Secondary Grid: Schedule Health + Work/Study Capacity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        <div className="h-full">
          <ScheduleHealthCard
            health={dashboardData?.health || null}
            loading={loading && !dashboardData}
          />
        </div>

        <div className="h-full">
          <WorkStudyCard
            work={dashboardData?.work || null}
            study={dashboardData?.study || null}
            loading={loading && !dashboardData}
            onAddStudyGoal={handleOpenAddStudyTask}
          />
        </div>
      </div>

      {/* 7. Recommendations Area */}
      <RecommendationsCard
        recommendations={dashboardData?.recommendations || []}
        loading={loading && !dashboardData}
      />

      {/* 8. Weekly Analytics Summary */}
      <WeekSummaryCard
        week={dashboardData?.week || null}
        studyHours={dashboardData?.analytics?.study_hours}
        currency={currency}
        loading={loading && !dashboardData}
      />

      {/* Quick Actions */}
      <div className="pt-2">
        <QuickActions
          onAddClass={handleOpenAddClass}
          onAddShift={handleOpenAddShift}
          onImport={handleOpenImport}
          onAddStudyTask={handleOpenAddStudyTask}
        />
      </div>

      {/* Modals */}
      <BlockModal
        isOpen={blockModalState.isOpen}
        defaultType={blockModalState.defaultType}
        onClose={handleCloseBlockModal}
      />

      <ImportModal
        isOpen={importModalOpen}
        onClose={handleCloseImportModal}
        onToast={(msg) => showSuccessToast(msg)}
      />

      <AddTaskModal
        isOpen={addTaskOpen}
        onClose={() => setAddTaskOpen(false)}
        onTaskCreated={(task: StudyTask) => {
          setAddTaskOpen(false);
          showSuccessToast(`"${task.title}" created! Redirecting to Planner.`);
          router.push('/student/planner');
        }}
      />
    </div>
  );
}

export default function StudentDashboardPage() {
  return (
    <CalendarProvider>
      <StudentDashboardContent />
    </CalendarProvider>
  );
}
