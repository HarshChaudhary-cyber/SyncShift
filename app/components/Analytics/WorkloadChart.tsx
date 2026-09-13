'use client';

import React from 'react';
import { DailyWorkloadItem } from '@/lib/api';

interface WorkloadChartProps {
  dailyWorkload: DailyWorkloadItem[];
  loading?: boolean;
}

export default function WorkloadChart({
  dailyWorkload,
  loading,
}: WorkloadChartProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-xl animate-pulse space-y-4">
        <div className="h-6 bg-[var(--bg-secondary)] rounded w-1/3" />
        <div className="space-y-3 pt-2">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="h-7 bg-[var(--bg-secondary)] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // Find max hours for scaling bars (minimum scale base 8h)
  const maxHours = Math.max(8, ...dailyWorkload.map((d) => d.total_hours));

  // Identify any heavy days
  const heavyDays = dailyWorkload.filter((d) => d.is_heavy);

  return (
    <div
      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl space-y-5"
      role="region"
      aria-label="Daily Workload Chart"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">📈</span>
          <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
            Daily Workload (Mon–Sun)
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-blue-500 inline-block" />
            Class
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-emerald-500 inline-block" />
            Work
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-purple-500 inline-block" />
            Study
          </span>
        </div>
      </div>

      {/* Heavy Day Callout Banner if any */}
      {heavyDays.length > 0 && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-800 dark:text-amber-200 text-xs flex items-center gap-2">
          <span className="text-sm shrink-0">⚠️</span>
          <span className="leading-snug">
            {heavyDays.map((d) => `${d.day} (${d.total_hours}h)`).join(', ')} scheduled — peak strain day. Ensure sufficient rest!
          </span>
        </div>
      )}

      {/* Horizontal Bar Chart (Clean, responsive, accessible) */}
      <div className="space-y-3 pt-1">
        {dailyWorkload.map((item) => {
          const classPct = (item.class_hours / maxHours) * 100;
          const workPct = (item.work_hours / maxHours) * 100;
          const studyPct = (item.study_hours / maxHours) * 100;

          return (
            <div key={item.day} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[var(--text-primary)] w-24 truncate">
                  {item.day}
                </span>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  {item.is_heavy && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-sans font-semibold bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                      Heavy day
                    </span>
                  )}
                  <span className="text-[var(--text-secondary)]">
                    {item.total_hours}h scheduled
                  </span>
                </div>
              </div>

              {/* Stacked Progress Bar */}
              <div className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg h-5.5 p-0.5 flex overflow-hidden">
                {item.total_hours === 0 ? (
                  <div className="w-full flex items-center justify-center text-[10px] text-[var(--text-muted)] italic">
                    Free day
                  </div>
                ) : (
                  <>
                    {classPct > 0 && (
                      <div
                        className="h-full bg-blue-500 hover:brightness-110 transition rounded-l-xs text-[10px] text-white flex items-center justify-center overflow-hidden px-1"
                        style={{ width: `${classPct}%` }}
                        title={`Class: ${item.class_hours}h`}
                      >
                        {classPct >= 12 && `${item.class_hours}h`}
                      </div>
                    )}
                    {workPct > 0 && (
                      <div
                        className="h-full bg-emerald-500 hover:brightness-110 transition text-[10px] text-white flex items-center justify-center overflow-hidden px-1"
                        style={{ width: `${workPct}%` }}
                        title={`Work: ${item.work_hours}h`}
                      >
                        {workPct >= 12 && `${item.work_hours}h`}
                      </div>
                    )}
                    {studyPct > 0 && (
                      <div
                        className="h-full bg-purple-500 hover:brightness-110 transition rounded-r-xs text-[10px] text-white flex items-center justify-center overflow-hidden px-1"
                        style={{ width: `${studyPct}%` }}
                        title={`Study: ${item.study_hours}h`}
                      >
                        {studyPct >= 12 && `${item.study_hours}h`}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Accessible Table Fallback for Screen Readers */}
      <div className="sr-only">
        <table>
          <caption>Weekly scheduled hours by day</caption>
          <thead>
            <tr>
              <th scope="col">Day</th>
              <th scope="col">Class Hours</th>
              <th scope="col">Work Hours</th>
              <th scope="col">Study Hours</th>
              <th scope="col">Total Hours</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {dailyWorkload.map((d) => (
              <tr key={d.day}>
                <td>{d.day}</td>
                <td>{d.class_hours}</td>
                <td>{d.work_hours}</td>
                <td>{d.study_hours}</td>
                <td>{d.total_hours}</td>
                <td>{d.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
