'use client';

import React, { useState } from 'react';
import {
  TimetableImpactResponse,
  StudentImpactDetail,
} from '@/lib/api';
import CustomSelect from '@/components/ui/CustomSelect';

interface TimetableImpactModalProps {
  isOpen: boolean;
  isLoading: boolean;
  impactData: TimetableImpactResponse | null;
  staleError: string | null;
  isApplying: boolean;
  onApply: () => void;
  onCancel: () => void;
  onRefresh?: () => void;
}

export default function TimetableImpactModal({
  isOpen,
  isLoading,
  impactData,
  staleError,
  isApplying,
  onApply,
  onCancel,
  onRefresh,
}: TimetableImpactModalProps) {
  const [activeTab, setActiveTab] = useState<'students' | 'room' | 'faculty'>('students');
  const [conflictFilter, setConflictFilter] = useState<string>('all');

  if (!isOpen) return null;

  const isBlocked = impactData?.is_blocked ?? false;
  const summary = impactData?.summary;
  const before = impactData?.before;
  const after = impactData?.after;
  const students = impactData?.student_impacts || [];

  // Filter students
  const filteredStudents = students.filter((s: StudentImpactDetail) => {
    if (conflictFilter === 'all') return true;
    if (conflictFilter === 'conflicts_only') return s.conflict_type !== 'none' && !s.is_resolved_conflict;
    if (conflictFilter === 'work') return s.conflict_type === 'work_shift';
    if (conflictFilter === 'class') return s.conflict_type === 'other_class';
    if (conflictFilter === 'availability') return s.conflict_type === 'unavailable' || s.conflict_type === 'hard_constraint';
    if (conflictFilter === 'resolved') return s.is_resolved_conflict;
    return true;
  });

  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case 'BLOCKED':
        return {
          label: 'BLOCKED',
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
          dot: 'bg-rose-500',
        };
      case 'HIGH':
        return {
          label: 'HIGH IMPACT',
          bg: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
          dot: 'bg-orange-500',
        };
      case 'MEDIUM':
        return {
          label: 'MEDIUM IMPACT',
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
          dot: 'bg-amber-500',
        };
      case 'LOW':
      default:
        return {
          label: 'LOW IMPACT',
          bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
          dot: 'bg-emerald-500',
        };
    }
  };

  const badgeInfo = getSeverityBadge(summary?.severity);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Review Timetable Change
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-semibold rounded-full border ${badgeInfo.bg}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${badgeInfo.dot}`}></span>
                {badgeInfo.label}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white mt-2">
              {before?.course_code || 'Course'} {before?.section_code ? `(${before.section_code})` : ''}
              {before?.course_name ? ` — ${before.course_name}` : ''}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Review affected students, rooms, and instructor schedules before applying this change.
            </p>
          </div>
          <button
            onClick={onCancel}
            disabled={isApplying}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {isLoading ? (
            <div className="py-16 text-center space-y-3">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
              <p className="text-sm text-slate-300 font-medium">Analyzing timetable impact...</p>
              <p className="text-xs text-slate-500">Evaluating enrolled student commitments and room availability</p>
            </div>
          ) : (
            <>
              {/* Stale Concurrency Warning */}
              {staleError && (
                <div className="p-4 bg-amber-950/40 border border-amber-600/50 rounded-xl text-amber-200 text-sm space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-amber-300">
                    <span>⚠️ Timetable Changed Concurrently</span>
                  </div>
                  <p>{staleError}</p>
                  {onRefresh && (
                    <button
                      onClick={onRefresh}
                      className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition-colors"
                    >
                      Refresh Timetable & Review Again
                    </button>
                  )}
                </div>
              )}

              {/* Blocked Alert Container */}
              {isBlocked && (
                <div className="p-4 bg-rose-950/40 border border-rose-600/60 rounded-xl text-rose-200 text-sm space-y-2">
                  <div className="flex items-center gap-2 font-bold text-rose-300 text-base">
                    <span>🚫 Can&apos;t Make This Change</span>
                  </div>
                  <p className="text-xs text-rose-200/90">
                    This proposed timetable change violates official university scheduling constraints:
                  </p>
                  <ul className="list-disc list-inside text-xs space-y-1 text-rose-300 font-medium">
                    {summary?.blocked_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                  <p className="text-xs text-slate-400 pt-1">
                    Please choose another time slot, assign another room, or cancel this change.
                  </p>
                </div>
              )}

              {/* Before vs After Comparison Card */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                {/* BEFORE */}
                <div className="space-y-2 border-b md:border-b-0 md:border-r border-slate-800 pb-3 md:pb-0 md:pr-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Current Schedule (Before)</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">Saved</span>
                  </div>
                  <div className="text-base font-semibold text-white">
                    {before?.day_name} • {before?.start_time} – {before?.end_time}
                  </div>
                  <div className="text-xs text-slate-400 flex flex-col gap-1">
                    <div>
                      🏢 <span className="text-slate-300">{before?.room_label || 'No room assigned'}</span>
                      {before?.room_capacity && ` (Capacity: ${before.room_capacity})`}
                    </div>
                    <div>
                      👨‍🏫 <span className="text-slate-300">{before?.faculty_name || 'No instructor override'}</span>
                    </div>
                  </div>
                </div>

                {/* AFTER */}
                <div className="space-y-2 md:pl-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">Proposed Change (After)</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      Pending
                    </span>
                  </div>
                  <div className="text-base font-bold text-indigo-300">
                    {after?.day_name} • {after?.start_time} – {after?.end_time}
                  </div>
                  <div className="text-xs text-slate-400 flex flex-col gap-1">
                    <div>
                      🏢 <span className="text-slate-300">{after?.room_label || 'No room assigned'}</span>
                      {after?.room_capacity && ` (Capacity: ${after.room_capacity})`}
                    </div>
                    <div>
                      👨‍🏫 <span className="text-slate-300">{after?.faculty_name || 'No instructor override'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Aggregate Impact Summary Cards (Aggregate First) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Students Affected</p>
                  <p className="text-2xl font-bold text-white mt-0.5">{summary?.students_affected ?? 0}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Enrolled in section</p>
                </div>

                <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">New Conflicts</p>
                  <p
                    className={`text-2xl font-bold mt-0.5 ${
                      (summary?.new_conflicts ?? 0) > 0 ? 'text-orange-400' : 'text-emerald-400'
                    }`}
                  >
                    {summary?.new_conflicts ?? 0}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {summary?.work_conflicts ?? 0} work • {summary?.availability_conflicts ?? 0} blackout
                  </p>
                </div>

                <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Resolved Conflicts</p>
                  <p className="text-2xl font-bold text-emerald-400 mt-0.5">{summary?.resolved_conflicts ?? 0}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Cleared by move</p>
                </div>

                <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Room & Faculty</p>
                  <p
                    className={`text-base font-bold mt-1 ${
                      isBlocked ? 'text-rose-400' : 'text-emerald-400'
                    }`}
                  >
                    {isBlocked ? 'Issue Detected' : 'All Clear'}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {summary?.room_issues.length ? 'Room overlap/cap' : 'Zero collisions'}
                  </p>
                </div>
              </div>

              {/* Tabs for Details */}
              <div className="border-b border-slate-800 flex items-center justify-between gap-4">
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveTab('students')}
                    className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
                      activeTab === 'students'
                        ? 'border-indigo-500 text-indigo-300'
                        : 'border-transparent text-slate-400 hover:text-white'
                    }`}
                  >
                    👥 Affected Students ({students.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('room')}
                    className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
                      activeTab === 'room'
                        ? 'border-indigo-500 text-indigo-300'
                        : 'border-transparent text-slate-400 hover:text-white'
                    }`}
                  >
                    🏢 Room Capacity & Details
                  </button>
                  <button
                    onClick={() => setActiveTab('faculty')}
                    className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
                      activeTab === 'faculty'
                        ? 'border-indigo-500 text-indigo-300'
                        : 'border-transparent text-slate-400 hover:text-white'
                    }`}
                  >
                    👨‍🏫 Faculty Schedule
                  </button>
                </div>

                {activeTab === 'students' && (
                  <div className="flex items-center gap-1.5 pb-2 w-64">
                    <CustomSelect
                      options={[
                        { value: 'all', label: `All Students (${students.length})` },
                        { value: 'conflicts_only', label: `New Conflicts Only (${summary?.new_conflicts ?? 0})` },
                        { value: 'work', label: `Work Conflicts (${summary?.work_conflicts ?? 0})` },
                        { value: 'class', label: `Class Clashes (${summary?.class_conflicts ?? 0})` },
                        { value: 'availability', label: `Blackouts (${summary?.availability_conflicts ?? 0})` },
                        { value: 'resolved', label: `Resolved (${summary?.resolved_conflicts ?? 0})` },
                      ]}
                      value={conflictFilter}
                      onChange={(val) => setConflictFilter(String(val))}
                      size="sm"
                      portalTheme="university"
                    />
                  </div>
                )}
              </div>

              {/* Tab 1: Affected Students List */}
              {activeTab === 'students' && (
                <div className="space-y-2">
                  {filteredStudents.length === 0 ? (
                    <div className="py-8 text-center text-slate-400 text-xs">
                      No student records match the selected filter.
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-800/80 max-h-56 overflow-y-auto pr-1">
                      {filteredStudents.map((s, idx) => (
                        <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center text-[10px] font-semibold">
                              {s.student_id}
                            </span>
                            <div>
                              <p className="font-semibold text-white">{s.student_name}</p>
                              <p className="text-slate-400 text-[11px]">{s.conflict_description}</p>
                            </div>
                          </div>

                          <div className="text-right">
                            {s.conflict_type === 'none' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-400">
                                Shifted (OK)
                              </span>
                            ) : s.is_resolved_conflict ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                ✓ Resolved
                              </span>
                            ) : s.conflict_type === 'work_shift' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-orange-500/20 text-orange-300 border border-orange-500/30">
                                Work Clash {s.overlap_time ? `(${s.overlap_time})` : ''}
                              </span>
                            ) : s.conflict_type === 'unavailable' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                Blackout {s.overlap_time ? `(${s.overlap_time})` : ''}
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                Class Clash {s.overlap_time ? `(${s.overlap_time})` : ''}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Room Capacity & Details */}
              {activeTab === 'room' && (
                <div className="space-y-4 p-2 text-xs">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl space-y-1">
                      <p className="text-slate-400 uppercase font-semibold text-[10px]">Assigned Room</p>
                      <p className="text-sm font-bold text-white">{after?.room_label || 'None assigned'}</p>
                      <p className="text-slate-400">
                        Room Capacity: <span className="text-white font-semibold">{after?.room_capacity ?? 'N/A'}</span>
                      </p>
                    </div>
                    <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl space-y-1">
                      <p className="text-slate-400 uppercase font-semibold text-[10px]">Section Enrollment</p>
                      <p className="text-sm font-bold text-white">
                        {before?.section_capacity ? `${summary?.students_affected || 0} / ${before.section_capacity} enrolled` : `${summary?.students_affected || 0} enrolled`}
                      </p>
                      <p className="text-slate-400">
                        Room Fit:{' '}
                        {after?.room_capacity && before?.section_capacity ? (
                          after.room_capacity >= before.section_capacity ? (
                            <span className="text-emerald-400 font-semibold">✓ Capacity Sufficient</span>
                          ) : (
                            <span className="text-rose-400 font-semibold">⚠ Undersized Room</span>
                          )
                        ) : (
                          <span className="text-slate-400">Unrestricted</span>
                        )}
                      </p>
                    </div>
                  </div>

                  {summary?.room_issues && summary.room_issues.length > 0 && (
                    <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-xl text-rose-300 space-y-1">
                      <p className="font-semibold">Room Issues Identified:</p>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                        {summary.room_issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Faculty Schedule */}
              {activeTab === 'faculty' && (
                <div className="space-y-3 p-2 text-xs">
                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl space-y-1">
                    <p className="text-slate-400 uppercase font-semibold text-[10px]">Assigned Faculty</p>
                    <p className="text-sm font-bold text-white">{after?.faculty_name || 'No instructor assigned'}</p>
                    <p className="text-slate-400">
                      Status:{' '}
                      {summary?.faculty_issues.length === 0 ? (
                        <span className="text-emerald-400 font-semibold">✓ No teaching overlap at this time</span>
                      ) : (
                        <span className="text-rose-400 font-semibold">⚠ Teaching overlap conflict</span>
                      )}
                    </p>
                  </div>

                  {summary?.faculty_issues && summary.faculty_issues.length > 0 && (
                    <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-xl text-rose-300 space-y-1">
                      <p className="font-semibold">Instructor Issues Identified:</p>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                        {summary.faculty_issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            {isBlocked ? (
              <span className="text-rose-400 font-medium">Resolving blocking constraints is required to apply.</span>
            ) : (
              <span>This change will update the authoritative university timetable for all enrolled students.</span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onCancel}
              disabled={isApplying}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
            >
              Cancel
            </button>

            {!isBlocked && (
              <button
                onClick={onApply}
                disabled={isApplying || isLoading}
                className="px-5 py-2 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md hover:shadow-indigo-500/25 transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {isApplying ? (
                  <>
                    <span className="animate-spin h-3 w-3 border-b-2 border-white rounded-full"></span>
                    <span>Applying...</span>
                  </>
                ) : (
                  <span>Apply Change</span>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
