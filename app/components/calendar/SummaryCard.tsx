'use client';

import React from 'react';
import { useCalendar } from '@/context/CalendarContext';
import { useAuthContext } from '@/context/AuthContext';

export default function SummaryCard() {
  const { totals } = useCalendar();
  const { user } = useAuthContext();
  const limit = user?.weekly_work_hour_limit ?? 20;
  const isOver = totals.over_limit || totals.shift_hours > limit;

  return (
    <div className="w-full bg-neutral-900/90 border border-neutral-800 rounded-xl p-4 shadow-lg backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* KPI metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 flex-1">
          {/* Shift Hours */}
          <div className="bg-neutral-950/70 border border-neutral-800/80 rounded-lg p-3">
            <div className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
              Shift Hours
            </div>
            <div className="mt-1 text-2xl font-bold text-emerald-400">
              {totals.shift_hours.toFixed(1)}
              <span className="text-xs font-normal text-neutral-400 ml-1">hrs</span>
            </div>
          </div>

          {/* Class Hours */}
          <div className="bg-neutral-950/70 border border-neutral-800/80 rounded-lg p-3">
            <div className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
              Class Hours
            </div>
            <div className="mt-1 text-2xl font-bold text-blue-400">
              {totals.class_hours.toFixed(1)}
              <span className="text-xs font-normal text-neutral-400 ml-1">hrs</span>
            </div>
          </div>

          {/* Expected Earnings */}
          <div className="bg-neutral-950/70 border border-neutral-800/80 rounded-lg p-3">
            <div className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
              Expected Earnings
            </div>
            <div className="mt-1 text-2xl font-bold text-neutral-100">
              ${totals.expected_earnings.toFixed(2)}
            </div>
          </div>

          {/* Work Limit Status */}
          <div
            className={`rounded-lg p-3 border transition-colors ${
              isOver
                ? 'bg-rose-950/40 border-rose-500/50'
                : 'bg-neutral-950/70 border-neutral-800/80'
            }`}
          >
            <div className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
              Work Limit
            </div>
            <div className="mt-1 text-2xl font-bold">
              <span className={isOver ? 'text-rose-400' : 'text-neutral-200'}>
                {totals.shift_hours.toFixed(1)}
              </span>
              <span className="text-xs font-normal text-neutral-500"> / {limit}h</span>
            </div>
          </div>
        </div>

        {/* Warning Badge if over limit */}
        {isOver && (
          <div className="sm:max-w-xs flex items-center gap-2 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs font-medium animate-pulse">
            <span className="text-base">⚠️</span>
            <span>
              <strong>Over Limit:</strong> {totals.shift_hours.toFixed(1)} hours/week (visa limit: {limit}h)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
