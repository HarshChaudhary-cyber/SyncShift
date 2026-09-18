'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { api, StudyTask } from '@/lib/api';
import AddTaskModal from '@/components/planner/AddTaskModal';
import { showErrorToast, showSuccessToast } from '@/lib/toast';

export default function StudentTasksPage() {
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all');

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getTasks();
      setTasks(data || []);
    } catch {
      showErrorToast('Failed to load study tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleToggleStatus = async (task: StudyTask) => {
    const isDone = task.status === 'done' || task.status === 'completed';
    const newStatus = isDone ? 'pending' : 'done';
    try {
      await api.updateTask(task.id, { status: newStatus });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)));
      showSuccessToast(isDone ? 'Task reopened' : 'Task completed! 🎉');
    } catch {
      showErrorToast('Failed to update task');
    }
  };

  const handleDelete = async (taskId: number, title: string) => {
    if (!confirm(`Delete task "${title}"?`)) return;
    try {
      await api.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      showSuccessToast(`Deleted "${title}"`);
    } catch {
      showErrorToast('Failed to delete task');
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const isDone = t.status === 'done' || t.status === 'completed';
    if (filter === 'pending') return !isDone;
    if (filter === 'completed') return isDone;
    return true;
  });

  const pendingCount = tasks.filter((t) => t.status !== 'done' && t.status !== 'completed').length;
  const completedCount = tasks.length - pendingCount;
  const totalEstimatedHours = tasks
    .filter((t) => t.status !== 'done' && t.status !== 'completed')
    .reduce((acc, t) => acc + (t.total_hours_required || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📝</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Study Tasks</h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Organize coursework, homework deadlines, and study targets for automatic smart planning.
          </p>
        </div>
        <button
          onClick={() => setAddModalOpen(true)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-indigo-950/20 self-start sm:self-auto"
        >
          + Add Study Task
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Pending Tasks</p>
          <p className="text-2xl font-black text-amber-400 mt-1">{pendingCount}</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Awaiting completion</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Estimated Study Time</p>
          <p className="text-2xl font-black text-indigo-400 mt-1">{totalEstimatedHours.toFixed(1)} hrs</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Required for pending tasks</p>
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
          <p className="text-xs font-medium text-[var(--text-muted)]">Completed</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{completedCount}</p>
          <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">Finished tasks</p>
        </div>
      </div>

      {/* Tasks Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        {/* Filters */}
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
          <h2 className="text-sm font-bold text-[var(--text-primary)]">Tasks List</h2>
          <div className="flex items-center gap-1 bg-[var(--bg-secondary)] p-1 rounded-xl">
            {(['all', 'pending', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition cursor-pointer capitalize ${
                  filter === f
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Loading tasks…
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <span className="text-4xl">📚</span>
            <p className="text-sm font-medium text-[var(--text-secondary)]">No tasks found</p>
            <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
              Create a study task with a deadline and duration to receive smart scheduling recommendations.
            </p>
            <button
              onClick={() => setAddModalOpen(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              Add First Task
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-color)]">
            {filteredTasks.map((task) => {
              const isDone = task.status === 'done' || task.status === 'completed';
              return (
                <div key={task.id} className="py-3.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <button
                      onClick={() => handleToggleStatus(task)}
                      className={`w-6 h-6 rounded-lg border flex items-center justify-center transition cursor-pointer shrink-0 ${
                        isDone
                          ? 'bg-emerald-500 border-emerald-500 text-white'
                          : 'border-[var(--border-color)] hover:border-indigo-500'
                      }`}
                      title={isDone ? 'Mark as pending' : 'Mark as done'}
                    >
                      {isDone && <span className="text-xs font-bold">✓</span>}
                    </button>
                    <div className="min-w-0">
                      <h3
                        className={`text-sm font-medium truncate ${
                          isDone ? 'line-through text-[var(--text-muted)]' : 'text-[var(--text-primary)]'
                        }`}
                      >
                        {task.title}
                      </h3>
                      <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                        {task.deadline ? `Due ${task.deadline}` : 'No deadline'} ·{' '}
                        {task.total_hours_required ? `${task.total_hours_required}h estimated` : 'Flexible duration'}
                        {task.priority && (
                          <span
                            className={`ml-2 px-1.5 py-0.2 rounded text-[10px] font-semibold uppercase ${
                              task.priority === 'high'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                            }`}
                          >
                            {task.priority}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(task.id, task.title)}
                    className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer"
                    title="Delete task"
                  >
                    🗑️
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Task Modal */}
      <AddTaskModal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onTaskCreated={() => {
          setAddModalOpen(false);
          fetchTasks();
          showSuccessToast('Task created!');
        }}
      />
    </div>
  );
}
