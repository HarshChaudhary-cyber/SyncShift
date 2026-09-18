'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useUniversity } from '../layout';
import {
  api,
  Timetable,
  CourseMeeting,
  TimetableImpactResponse,
  TimetableChangeProposal,
} from '@/lib/api';
import { showErrorToast, showSuccessToast } from '@/lib/toast';
import CustomSelect from '@/components/ui/CustomSelect';

const DAYS = [
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' },
  { value: 0, label: 'Sunday' },
];

export default function UniversityImpactAnalysisPage() {
  const { institution, isAdmin } = useUniversity();
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [selectedTimetableId, setSelectedTimetableId] = useState<number | null>(null);
  const [meetings, setMeetings] = useState<CourseMeeting[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<number | null>(null);

  // Proposal State
  const [proposedDay, setProposedDay] = useState<number>(2); // Tuesday
  const [proposedStart, setProposedStart] = useState<string>('17:00:00');
  const [proposedEnd, setProposedEnd] = useState<string>('18:30:00');

  // Analysis result
  const [analyzing, setAnalyzing] = useState(false);
  const [impactResult, setImpactResult] = useState<TimetableImpactResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadTimetables = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      const data = await api.getTimetables(institution.id);
      setTimetables(data || []);
      if (data && data.length > 0) {
        setSelectedTimetableId(data[0].id);
      }
    } catch {
      showErrorToast('Failed to load timetables');
    } finally {
      setLoading(false);
    }
  }, [institution]);

  useEffect(() => {
    loadTimetables();
  }, [loadTimetables]);

  // Load meetings when timetable is selected
  useEffect(() => {
    if (!institution || !selectedTimetableId) return;
    async function fetchMeetings() {
      try {
        const data = await api.getMeetings(institution!.id, selectedTimetableId!);
        setMeetings(data || []);
        if (data && data.length > 0) {
          setSelectedMeetingId(data[0].id);
        } else {
          setSelectedMeetingId(null);
        }
      } catch (err) {
        console.warn('Unable to load timetable meetings:', err);
        setMeetings([]);
      }
    }
    fetchMeetings();
  }, [institution, selectedTimetableId]);

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !selectedTimetableId || !selectedMeetingId) {
      showErrorToast('Please select a timetable and class meeting first.');
      return;
    }

    try {
      setAnalyzing(true);
      setImpactResult(null);

      const payload: TimetableChangeProposal = {
        meeting_id: selectedMeetingId,
        day_of_week: proposedDay,
        start_time: proposedStart,
        end_time: proposedEnd,
      };

      const result = await api.previewTimetableChange(institution.id, selectedTimetableId, payload);
      setImpactResult(result);
      showSuccessToast('Impact analysis calculated successfully!');
    } catch (err: unknown) {
      showErrorToast(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const selectedMeeting = meetings.find((m) => m.id === selectedMeetingId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Timetable Impact Analysis
            </h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Simulate timetable schedule adjustments, identify affected enrolled students, and quantify student conflicts before publishing.
          </p>
        </div>
        {selectedTimetableId && (
          <Link
            href={`/university/timetables/${selectedTimetableId}`}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-950/20 self-start sm:self-auto"
          >
            Open in Timetable Editor →
          </Link>
        )}
      </div>

      {/* Simulator Control Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-5">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Change Simulation Parameters</h2>

        {loading ? (
          <div className="py-8 text-center text-xs text-[var(--text-secondary)]">Loading timetable data…</div>
        ) : timetables.length === 0 ? (
          <div className="py-8 text-center space-y-2">
            <p className="text-xs text-[var(--text-secondary)]">No timetables found in this institution.</p>
            <Link href="/university/timetables" className="text-xs font-semibold text-emerald-400 underline">
              Create a timetable first
            </Link>
          </div>
        ) : (
          <form onSubmit={handleRunAnalysis} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Select Timetable */}
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                  Select Timetable
                </label>
                <CustomSelect
                  options={timetables.map((t) => ({
                    value: String(t.id),
                    label: `${t.name} (${t.status})`,
                  }))}
                  value={selectedTimetableId ? String(selectedTimetableId) : ''}
                  onChange={(val) => setSelectedTimetableId(Number(val))}
                  placeholder="Choose timetable..."
                  searchable
                  portalTheme="university"
                />
              </div>

              {/* Select Class Meeting */}
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                  Target Class Meeting to Reschedule
                </label>
                <CustomSelect
                  options={
                    meetings.length === 0
                      ? [{ value: '', label: 'No meetings in this timetable', disabled: true }]
                      : meetings.map((m) => ({
                          value: String(m.id),
                          label: `${m.section_code || `Section #${m.section_id}`} · ${DAYS.find((d) => d.value === m.day_of_week)?.label || `Day ${m.day_of_week}`} (${m.start_time.slice(0, 5)} - ${m.end_time.slice(0, 5)})`,
                        }))
                  }
                  value={selectedMeetingId ? String(selectedMeetingId) : ''}
                  onChange={(val) => setSelectedMeetingId(Number(val))}
                  disabled={meetings.length === 0}
                  placeholder="Choose meeting to reschedule..."
                  searchable
                  portalTheme="university"
                />
              </div>
            </div>

            {/* Current vs Proposed Time Grid */}
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-3">
              <div className="text-xs font-bold text-[var(--text-primary)]">Proposed New Schedule</div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] text-[var(--text-muted)] mb-1">Proposed Day</label>
                  <CustomSelect
                    options={DAYS.map((d) => ({
                      value: String(d.value),
                      label: d.label,
                    }))}
                    value={String(proposedDay)}
                    onChange={(val) => setProposedDay(Number(val))}
                    size="sm"
                    portalTheme="university"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--text-muted)] mb-1">Start Time (HH:MM:SS)</label>
                  <input
                    type="text"
                    value={proposedStart}
                    onChange={(e) => setProposedStart(e.target.value)}
                    placeholder="17:00:00"
                    className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[var(--text-muted)] mb-1">End Time (HH:MM:SS)</label>
                  <input
                    type="text"
                    value={proposedEnd}
                    onChange={(e) => setProposedEnd(e.target.value)}
                    placeholder="18:30:00"
                    className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Submit button */}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={analyzing || !selectedMeetingId}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-950/20 cursor-pointer flex items-center gap-2"
              >
                {analyzing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Calculating Impact Engine…</span>
                  </>
                ) : (
                  <>
                    <span>⚡</span>
                    <span>Run Impact Analysis</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Analysis Results */}
      {impactResult && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-5 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
            <h2 className="text-base font-bold text-[var(--text-primary)]">Impact Analysis Results</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Simulation Complete
            </span>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
              <p className="text-[11px] text-[var(--text-muted)]">Affected Students</p>
              <p className="text-2xl font-black text-amber-400 mt-1">
                {impactResult.summary.students_affected}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
              <p className="text-[11px] text-[var(--text-muted)]">New Conflicts</p>
              <p className="text-2xl font-black text-rose-400 mt-1">
                {impactResult.summary.new_conflicts}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
              <p className="text-[11px] text-[var(--text-muted)]">Work / Life Conflicts</p>
              <p className="text-2xl font-black text-yellow-400 mt-1">
                {impactResult.summary.work_conflicts + impactResult.summary.personal_conflicts}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
              <p className="text-[11px] text-[var(--text-muted)]">Resolved Conflicts</p>
              <p className="text-2xl font-black text-indigo-400 mt-1">
                {impactResult.summary.resolved_conflicts}
              </p>
            </div>
          </div>

          {/* Student Breakdown */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-[var(--text-primary)]">Impacted Student Breakdown</h3>
            {impactResult.student_impacts && impactResult.student_impacts.length > 0 ? (
              <div className="divide-y divide-[var(--border-color)] border border-[var(--border-color)] rounded-xl overflow-hidden">
                {impactResult.student_impacts.map((impact, idx) => (
                  <div key={idx} className="p-3.5 flex items-center justify-between text-xs bg-[var(--bg-card)]">
                    <div>
                      <span className="font-semibold text-[var(--text-primary)]">
                        {impact.student_name || `Student #${impact.student_id}`}
                      </span>
                      <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                        {impact.conflict_description || `Type: ${impact.conflict_type}`}
                        {impact.overlap_time ? ` (${impact.overlap_time})` : ''}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        impact.is_new_conflict
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}
                    >
                      {impact.conflict_type}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-xs text-emerald-300">
                ✓ No enrolled student schedule conflicts detected for this proposed change!
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
