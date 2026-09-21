'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, PlanOption, PlanPreviewResponse, SmartPlanPreviewResponse, StudyTask } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { CalendarProvider, useCalendar } from '@/context/CalendarContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';
import AddTaskModal from '@/components/planner/AddTaskModal';
import PlanPreviewModal from '@/components/planner/PlanPreviewModal';
import WeeklyPlanHero from '@/components/planner/WeeklyPlanHero';
import PlanOptionsModal from '@/components/planner/PlanOptionsModal';
import { showSuccessToast, showErrorToast } from '@/lib/toast';

export function PlannerContent({ showNavbar = true }: { showNavbar?: boolean }) {
  const router = useRouter();
  const { status } = useAuthContext();
  const { refreshWeek } = useCalendar();

  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<{ task: StudyTask; isReplan: boolean } | null>(null);

  // N5 Smart Planning state
  const [smartPreview, setSmartPreview] = useState<SmartPlanPreviewResponse | null>(null);
  const [isSmartPlanModalOpen, setIsSmartPlanModalOpen] = useState(false);
  const [isSmartPlanningLoading, setIsSmartPlanningLoading] = useState(false);
  const [isApplyingSmartPlan, setIsApplyingSmartPlan] = useState(false);
  const [hasAppliedSmartPlan, setHasAppliedSmartPlan] = useState(false);

  // Single-task planner modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [planningTask, setPlanningTask] = useState<StudyTask | null>(null);
  const [planPreview, setPlanPreview] = useState<PlanPreviewResponse | null>(null);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Done section collapsible
  const [isDoneSectionOpen, setIsDoneSectionOpen] = useState(false);

  const fetchTasks = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    setError(null);
    try {
      const data = await api.getTasks();
      setTasks(data);
    } catch (err: any) {
      if (err?.status === 401) {
        router.replace('/login');
        return;
      }
      setError(err?.message || 'Failed to load study tasks');
    } finally {
      setLoading(false);
    }
  }, [router]);

  const fetchSmartPlanningSummary = useCallback(async () => {
    try {
      const prev = await api.previewSmartPlan();
      setSmartPreview(prev);
    } catch {
      // Non-blocking background fetch
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchSmartPlanningSummary();
  }, [fetchTasks, fetchSmartPlanningSummary]);

  // Handle Weekly Smart Planning Preview Trigger
  const handleTriggerSmartPlanning = async () => {
    setIsSmartPlanningLoading(true);
    try {
      const prev = await api.previewSmartPlan();
      setSmartPreview(prev);
      if (!prev.has_feasible_solution && prev.blocking_issues?.length > 0) {
        showErrorToast(`Could not create fully conflict-free plan: ${prev.blocking_issues[0]}`);
      }
      setIsSmartPlanModalOpen(true);
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to generate weekly smart plan');
    } finally {
      setIsSmartPlanningLoading(false);
    }
  };

  // Handle Applying Selected Plan Strategy
  const handleApplySmartPlan = async (option: PlanOption) => {
    if (!smartPreview) return;
    setIsApplyingSmartPlan(true);
    try {
      const res = await api.applySmartPlan({
        option_id: option.id,
        week_start: smartPreview.week_start,
        approved_new_blocks: option.added_blocks.map((b) => ({
          title: b.title,
          day_of_week: b.day_of_week,
          date: b.date,
          start_time: b.start_time,
          end_time: b.end_time,
          duration_hours: b.duration_hours,
          study_task_id: b.study_task_id ?? undefined,
          course_id: b.course_id ?? undefined,
          type: 'study',
        })),
      });

      showSuccessToast(`Plan "${option.name}" applied! +${res.created_blocks_count} study blocks added. Zero conflicts.`);
      setHasAppliedSmartPlan(true);
      setIsSmartPlanModalOpen(false);
      refreshWeek();
      fetchTasks(true);
      fetchSmartPlanningSummary();
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to apply plan to calendar');
    } finally {
      setIsApplyingSmartPlan(false);
    }
  };

  // Handle Reverting Weekly Plan
  const handleRevertSmartPlan = async () => {
    if (!smartPreview) return;
    if (!confirm('Revert planned study sessions for this week?')) return;
    try {
      const res = await api.revertSmartPlan(smartPreview.week_start);
      showSuccessToast(res.message || 'Planned study sessions reverted.');
      setHasAppliedSmartPlan(false);
      refreshWeek();
      fetchTasks(true);
      fetchSmartPlanningSummary();
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to revert plan');
    }
  };

  // Handle plan generation (Auto-schedule or Replan)
  const handleGeneratePlan = async (task: StudyTask, isReplan: boolean = false) => {
    setActionLoadingId(task.id);
    setPlanError(null);
    try {
      const plan = isReplan
        ? await api.replanTask(task.id)
        : await api.planTask(task.id);

      setPlanningTask(task);
      setPlanPreview(plan);
      setIsPreviewModalOpen(true);
    } catch (err: any) {
      setPlanError({ task, isReplan });
      showErrorToast("We couldn't generate study recommendations right now.");
    } finally {
      setActionLoadingId(null);
    }
  };

  // Handle Mark Done (Completes full task & hours)
  const handleMarkDone = async (task: StudyTask) => {
    try {
      const updated = await api.completeTask(task.id);
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
      refreshWeek();
      showSuccessToast(`Marked "${task.title}" as completed! 🎉`);
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to complete task');
    }
  };

  // Handle Incremental Progress
  const handleAddProgress = async (task: StudyTask, additionalHours: number) => {
    try {
      const currentCompleted = task.completed_hours ?? task.hours_done ?? 0;
      const newCompleted = Math.min(task.total_hours_required, Math.round((currentCompleted + additionalHours) * 10) / 10);
      const isDone = newCompleted >= task.total_hours_required;
      const updated = await api.updateTask(task.id, {
        completed_hours: newCompleted,
        status: isDone ? 'done' : task.status,
      });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
      refreshWeek();
      showSuccessToast(
        isDone
          ? `Target reached for "${task.title}"! 🎉`
          : `Logged +${additionalHours}h progress on "${task.title}"`
      );
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to update progress');
    }
  };

  // Handle Delete
  const handleDeleteTask = async (taskId: number, title: string) => {
    if (!confirm(`Delete study task "${title}" and remove its scheduled study blocks?`)) {
      return;
    }
    try {
      await api.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      refreshWeek();
      showSuccessToast(`Deleted task "${title}"`);
    } catch (err: any) {
      showErrorToast(err?.message || 'Failed to delete task');
    }
  };

  // Deadline urgency helper
  const getDeadlineInfo = (deadlineStr: string) => {
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const due = new Date(deadlineStr + 'T00:00:00');
      const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays < 0) return { text: 'Past due', isUrgent: true, isLate: true };
      if (diffDays === 0) return { text: 'Due today!', isUrgent: true, isLate: false };
      if (diffDays === 1) return { text: 'Due tomorrow', isUrgent: true, isLate: false };
      if (diffDays <= 3) return { text: `Due in ${diffDays} days`, isUrgent: true, isLate: false };
      return { text: `Due ${due.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`, isUrgent: false, isLate: false };
    } catch {
      return { text: deadlineStr, isUrgent: false, isLate: false };
    }
  };

  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const activeTasks = tasks.filter((t) => t.status !== 'done');
  const completedTasks = tasks.filter((t) => t.status === 'done');

  const content = (
    <div className="max-w-5xl w-full mx-auto space-y-6">
      {/* N5 Weekly Smart Planning Hero */}
      <WeeklyPlanHero
        onPlanClick={handleTriggerSmartPlanning}
        isLoading={isSmartPlanningLoading}
        contextSummary={smartPreview?.context_summary}
        onRevertClick={handleRevertSmartPlan}
        hasAppliedPlan={hasAppliedSmartPlan}
      />

        {/* Study Tasks Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl backdrop-blur-md">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-2xl">🎯</span>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                Study Goals & Deadlines
              </h2>
            </div>
            <p className="text-xs text-indigo-400 font-medium mt-1">
              Plan classes, work, and life in one schedule.
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Add upcoming deadlines. SyncShift automatically discovers conflict-free gaps between your university classes and work shifts.
            </p>
          </div>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs sm:text-sm font-bold transition shadow-md shadow-purple-950/50 flex items-center justify-center gap-2 shrink-0 cursor-pointer"
          >
            <span>+</span>
            <span>Add Study Task</span>
          </button>
        </div>

        {/* Error state */}
        {error && (
          <div className="p-4 bg-rose-50 dark:bg-red-950/40 border border-rose-200 dark:border-red-800/80 rounded-2xl text-xs text-rose-700 dark:text-red-300 flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button onClick={() => fetchTasks(false)} className="underline font-semibold cursor-pointer">
              Try again
            </button>
          </div>
        )}

        {/* Plan generation error state */}
        {planError && (
          <div className="p-4 bg-rose-50 dark:bg-red-950/40 border border-rose-200 dark:border-red-800/80 rounded-2xl text-xs text-rose-700 dark:text-red-300 flex items-center justify-between gap-3">
            <span>⚠️ We couldn't generate study recommendations right now.</span>
            <button
              onClick={() => {
                const target = planError;
                setPlanError(null);
                handleGeneratePlan(target.task, target.isReplan);
              }}
              className="underline font-semibold cursor-pointer shrink-0"
            >
              Try again
            </button>
          </div>
        )}

        {/* Loading Skeletons */}
        {loading && (
          <div className="space-y-4 animate-pulse">
            <div className="h-28 bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)]" />
            <div className="h-28 bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)]" />
          </div>
        )}

        {/* Active Tasks List */}
        {!loading && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] px-1">
              <span>Active Tasks ({activeTasks.length})</span>
            </div>

            {activeTasks.length === 0 ? (
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-10 text-center space-y-3">
                <div className="text-4xl">📚</div>
                <h3 className="text-base font-bold text-[var(--text-primary)]">No study goals yet.</h3>
                <p className="text-xs text-[var(--text-secondary)] max-w-sm mx-auto">
                  Create a goal and SyncShift can suggest study sessions.
                </p>
                <button
                  onClick={() => setIsAddModalOpen(true)}
                  className="mt-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  Create study goal
                </button>
              </div>
            ) : (
              activeTasks.map((task) => {
                const deadlineInfo = getDeadlineInfo(task.deadline);
                const completedHours = task.completed_hours ?? task.hours_done ?? 0;
                const remainingHours = Math.max(0, Math.round((task.total_hours_required - completedHours) * 10) / 10);
                const percentDone = Math.min(
                  100,
                  task.total_hours_required > 0
                    ? Math.round((completedHours / task.total_hours_required) * 100)
                    : 0
                );
                const percentScheduled = Math.min(
                  100,
                  task.total_hours_required > 0
                    ? Math.round((task.hours_scheduled / task.total_hours_required) * 100)
                    : 0
                );

                const isActionLoading = actionLoadingId === task.id;

                return (
                  <div
                    key={task.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl transition hover:border-[var(--border-hover)] space-y-4"
                  >
                    {/* Top Row: Title, Course Chip, Badges */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <div className="flex flex-wrap items-center gap-2.5">
                        <span className="text-base sm:text-lg font-bold text-[var(--text-primary)] tracking-tight">
                          {task.title}
                        </span>

                        {task.course && (
                          <span
                            className="text-[11px] font-mono px-2.5 py-0.5 rounded-md font-semibold border shadow-xs"
                            style={{
                              backgroundColor: `${task.course.color}20`,
                              borderColor: `${task.course.color}50`,
                              color: task.course.color,
                            }}
                          >
                            {task.course.code}
                          </span>
                        )}

                        {task.priority && (
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                              task.priority === 'high'
                                ? 'bg-rose-500/15 text-rose-500 border-rose-500/30'
                                : task.priority === 'low'
                                ? 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                                : 'bg-amber-500/15 text-amber-500 border-amber-500/30'
                            }`}
                          >
                            {task.priority} priority
                          </span>
                        )}

                        {task.preferred_duration && (
                          <span className="text-[10px] font-medium text-[var(--text-muted)] bg-[var(--bg-secondary)] px-2 py-0.5 rounded-full border border-[var(--border-color)]">
                            ⏱️ {task.preferred_duration}m slots
                          </span>
                        )}

                        <span
                          suppressHydrationWarning
                          className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                            deadlineInfo.isUrgent
                              ? 'bg-rose-500/10 border-rose-500/40 text-rose-600 dark:text-rose-400'
                              : 'bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-secondary)]'
                          }`}
                        >
                          ⏳ {deadlineInfo.text}
                        </span>
                      </div>

                      {/* Status badge */}
                      <span
                        className={`text-[11px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full self-start sm:self-auto border ${
                          task.status === 'scheduled'
                            ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30'
                            : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {task.status === 'scheduled' ? 'Scheduled' : 'Pending Plan'}
                      </span>
                    </div>

                    {/* Progress Bar & Hours */}
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center justify-between text-xs text-[var(--text-secondary)] gap-1">
                        <span>
                          <strong className="text-emerald-500 font-semibold">{completedHours}h</strong> completed ·{' '}
                          {task.hours_scheduled}h scheduled ·{' '}
                          {remainingHours > 0 ? (
                            <span>{remainingHours}h remaining</span>
                          ) : (
                            <span className="text-emerald-500 font-semibold">Goal reached!</span>
                          )}{' '}
                          of <strong className="text-[var(--text-primary)]">{task.total_hours_required}h target</strong>
                        </span>
                        <span className="font-mono">{percentScheduled}% planned</span>
                      </div>

                      {/* Bar */}
                      <div className="w-full h-2.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border-color)] flex">
                        {/* Done portion (Green) */}
                        <div
                          style={{ width: `${percentDone}%` }}
                          className="h-full bg-emerald-500 transition-all duration-300"
                        />
                        {/* Scheduled future portion (Purple) */}
                        <div
                          style={{ width: `${Math.max(0, percentScheduled - percentDone)}%` }}
                          className="h-full bg-purple-500 transition-all duration-300"
                        />
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="pt-2 border-t border-[var(--border-color)] flex flex-wrap items-center justify-between gap-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        {task.hours_scheduled === 0 ? (
                          <button
                            onClick={() => handleGeneratePlan(task, false)}
                            disabled={isActionLoading}
                            className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold transition shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            <span>✨</span>
                            <span>{isActionLoading ? 'Finding Gaps…' : 'Auto-schedule'}</span>
                          </button>
                        ) : (
                          <button
                            onClick={() => handleGeneratePlan(task, true)}
                            disabled={isActionLoading}
                            className="px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-xl text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                            title="Clear future slots and recalculate fresh free gaps"
                          >
                            <span>↻</span>
                            <span>{isActionLoading ? 'Replanning…' : 'Replan'}</span>
                          </button>
                        )}

                        <button
                          onClick={() => handleAddProgress(task, 1.0)}
                          disabled={remainingHours <= 0}
                          className="px-2.5 py-1.5 bg-[var(--bg-secondary)] hover:bg-emerald-500/15 text-[var(--text-secondary)] hover:text-emerald-500 border border-[var(--border-color)] hover:border-emerald-500/30 rounded-xl text-xs font-semibold transition cursor-pointer disabled:opacity-40"
                          title="Log 1 hour completed"
                        >
                          +1h Done
                        </button>

                        <button
                          onClick={() => handleMarkDone(task)}
                          className="px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-emerald-500/10 text-[var(--text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-300 border border-[var(--border-color)] hover:border-emerald-500/30 rounded-xl text-xs font-medium transition cursor-pointer"
                        >
                          ✓ Complete
                        </button>
                      </div>

                      <button
                        onClick={() => handleDeleteTask(task.id, task.title)}
                        className="text-xs text-[var(--text-muted)] hover:text-rose-500 transition cursor-pointer px-2 py-1"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Collapsible Done Section */}
        {completedTasks.length > 0 && (
          <div className="pt-4">
            <button
              onClick={() => setIsDoneSectionOpen(!isDoneSectionOpen)}
              className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer mb-3"
            >
              <span>{isDoneSectionOpen ? '▼' : '▶'}</span>
              <span>Completed Tasks ({completedTasks.length})</span>
            </button>

            {isDoneSectionOpen && (
              <div className="space-y-3">
                {completedTasks.map((task) => (
                  <div
                    key={task.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 flex items-center justify-between gap-3 text-[var(--text-muted)]"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-emerald-500 font-bold">✓</span>
                      <div>
                        <span className="text-sm font-semibold line-through text-[var(--text-secondary)]">
                          {task.title}
                        </span>
                        <p className="text-xs text-[var(--text-muted)]">
                          {task.total_hours_required}h completed · Deadline was {task.deadline}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteTask(task.id, task.title)}
                      className="text-xs text-[var(--text-muted)] hover:text-rose-500 transition cursor-pointer"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      {/* Add Task Modal */}
      <AddTaskModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onTaskCreated={(newTask) => {
          setTasks((prev) => [newTask, ...prev]);
          showSuccessToast(`Created study task "${newTask.title}"`);
          // Automatically trigger plan preview for immediate convenience
          handleGeneratePlan(newTask, false);
        }}
      />

      {/* Plan Preview / Confirm Modal */}
      <PlanPreviewModal
        isOpen={isPreviewModalOpen}
        task={planningTask}
        plan={planPreview}
        onClose={() => {
          setIsPreviewModalOpen(false);
          setPlanningTask(null);
          setPlanPreview(null);
        }}
        onPlanConfirmed={(updatedTask) => {
          setTasks((prev) => prev.map((t) => (t.id === updatedTask.id ? updatedTask : t)));
          refreshWeek();
          showSuccessToast('✓ Study session added to calendar');
        }}
      />

      {/* N5 Weekly Smart Plan Options Modal */}
      <PlanOptionsModal
        isOpen={isSmartPlanModalOpen}
        onClose={() => setIsSmartPlanModalOpen(false)}
        previewData={smartPreview}
        onApplyPlan={handleApplySmartPlan}
        isApplying={isApplyingSmartPlan}
      />
    </div>
  );

  if (!showNavbar) {
    return content;
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col selection:bg-purple-500/30 selection:text-purple-200">
      <Navbar />
      <main className="flex-1 w-full px-4 sm:px-6 py-6 sm:py-8">
        {content}
      </main>
    </div>
  );
}

export default function PlannerPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/student/planner');
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    </ProtectedRoute>
  );
}
