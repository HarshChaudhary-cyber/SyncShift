'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useUniversity } from '../../layout';
import {
  api,
  Timetable,
  CourseMeeting,
  CourseMeetingCreatePayload,
  CourseMeetingUpdatePayload,
  AcademicSection,
  Room,
  FacultyProfile,
  TimetableChangeProposal,
  TimetableImpactResponse,
  TimetableChangeApplyRequest,
  PublishVersionResponse,
  getErrorMessage,
} from '@/lib/api';
import CalendarWeekView, { TimeBlock } from '@/components/CalendarWeekView';
import TimetableImpactModal from '@/components/university/TimetableImpactModal';
import TimetablePublishModal from '@/components/university/TimetablePublishModal';
import CustomSelect from '@/components/ui/CustomSelect';

const DAYS_OF_WEEK = [
  { value: 1, label: 'Monday', short: 'Mon' },
  { value: 2, label: 'Tuesday', short: 'Tue' },
  { value: 3, label: 'Wednesday', short: 'Wed' },
  { value: 4, label: 'Thursday', short: 'Thu' },
  { value: 5, label: 'Friday', short: 'Fri' },
  { value: 6, label: 'Saturday', short: 'Sat' },
  { value: 0, label: 'Sunday', short: 'Sun' },
];

const DAY_NAME_TO_INT: Record<string, number> = {
  Sunday: 0,
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
  Saturday: 6,
};

const MEETING_TYPES = [
  { value: 'lecture', label: 'Lecture' },
  { value: 'laboratory', label: 'Laboratory' },
  { value: 'tutorial', label: 'Tutorial' },
  { value: 'seminar', label: 'Seminar' },
  { value: 'practical', label: 'Practical' },
  { value: 'other', label: 'Other' },
];

export default function TimetableDetailPage() {
  const params = useParams();
  const router = useRouter();
  const timetableId = Number(params?.id);
  const { institution, isAdmin } = useUniversity();

  const [timetable, setTimetable] = useState<Timetable | null>(null);
  const [meetings, setMeetings] = useState<CourseMeeting[]>([]);
  const [sections, setSections] = useState<AcademicSection[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [facultyList, setFacultyList] = useState<FacultyProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // View mode: 'calendar' | 'list'
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');
  const [filterDay, setFilterDay] = useState<string>('all');
  const [filterRoom, setFilterRoom] = useState<string>('all');

  // Meeting modal state
  const [meetingModalOpen, setMeetingModalOpen] = useState(false);
  const [editingMeeting, setEditingMeeting] = useState<CourseMeeting | null>(null);
  const [meetingForm, setMeetingForm] = useState<CourseMeetingCreatePayload>({
    section_id: 0,
    day_of_week: 1,
    start_time: '09:00',
    end_time: '10:15',
    room_id: undefined,
    faculty_id: undefined,
    meeting_type: 'lecture',
    status: 'scheduled',
  });
  const [submittingMeeting, setSubmittingMeeting] = useState(false);
  const [meetingError, setMeetingError] = useState<string | null>(null);

  // Timetable edit modal state
  const [editTimetableOpen, setEditTimetableOpen] = useState(false);
  const [ttName, setTtName] = useState('');
  const [ttDescription, setTtDescription] = useState('');
  const [submittingTt, setSubmittingTt] = useState(false);

  // ── Task N6 Proposed Change & Impact Analysis State ──────────────────────
  interface ProposedMeetingChange {
    meeting: CourseMeeting;
    proposal: TimetableChangeProposal;
  }
  const [proposedChange, setProposedChange] = useState<ProposedMeetingChange | null>(null);
  const [impactData, setImpactData] = useState<TimetableImpactResponse | null>(null);
  const [isImpactLoading, setIsImpactLoading] = useState(false);
  const [isApplyingChange, setIsApplyingChange] = useState(false);
  const [impactModalOpen, setImpactModalOpen] = useState(false);
  const [staleError, setStaleError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // ── Task N7 / N8 Timetable Publish Modal State ───────────────────────────
  const [publishModalOpen, setPublishModalOpen] = useState(false);

  // Load all data
  const loadData = useCallback(async () => {
    if (!institution || !timetableId) return;
    try {
      setLoading(true);
      setError(null);
      const [ttData, meetingsData, sectionsData, roomsData, facultyData] = await Promise.all([
        api.getTimetable(institution.id, timetableId),
        api.getMeetings(institution.id, timetableId),
        api.getSections(institution.id),
        api.getRooms(institution.id, { status: 'active' }),
        api.getFaculty(institution.id, { status: 'active' }),
      ]);
      setTimetable(ttData);
      setMeetings(meetingsData);
      setSections(sectionsData);
      setRooms(roomsData);
      setFacultyList(facultyData);
      setTtName(ttData.name);
      setTtDescription(ttData.description || '');

      // Set default section in form if empty
      if (meetingForm.section_id === 0 && sectionsData.length > 0) {
        setMeetingForm((prev) => ({ ...prev, section_id: sectionsData[0].id }));
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load timetable details'));
    } finally {
      setLoading(false);
    }
  }, [institution, timetableId, meetingForm.section_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Trigger preview analysis for a proposed change (read-only, does not commit)
  const triggerPreviewChange = async (meeting: CourseMeeting, proposal: TimetableChangeProposal) => {
    if (!institution || !timetableId) return;
    setProposedChange({ meeting, proposal });
    setStaleError(null);
    setIsImpactLoading(true);
    setImpactModalOpen(true);

    try {
      const res = await api.previewTimetableChange(institution.id, timetableId, proposal);
      setImpactData(res);
    } catch (err: unknown) {
      setStaleError(getErrorMessage(err, 'Failed to calculate timetable impact.'));
    } finally {
      setIsImpactLoading(false);
    }
  };

  // Explicitly apply confirmed proposed change
  const handleApplyProposedChange = async () => {
    if (!institution || !timetableId || !proposedChange) return;

    try {
      setIsApplyingChange(true);
      setStaleError(null);

      const payload: TimetableChangeApplyRequest = {
        meeting_id: proposedChange.proposal.meeting_id,
        day_of_week: proposedChange.proposal.day_of_week,
        start_time: proposedChange.proposal.start_time,
        end_time: proposedChange.proposal.end_time,
        room_id: proposedChange.proposal.room_id,
        faculty_id: proposedChange.proposal.faculty_id,
        meeting_type: proposedChange.proposal.meeting_type,
        expected_updated_at: proposedChange.meeting.updated_at,
      };

      const res = await api.applyTimetableChange(institution.id, timetableId, payload);

      setImpactModalOpen(false);
      setProposedChange(null);
      setImpactData(null);

      const crsCode = res.meeting.course_code || 'Class';
      const dayStr = DAYS_OF_WEEK.find((d) => d.value === res.meeting.day_of_week)?.label || '';
      setSuccessNotice(
        `Timetable updated: ${crsCode} moved to ${dayStr} ${res.meeting.start_time.substring(0, 5)}–${res.meeting.end_time.substring(0, 5)}. ` +
        `${res.impact_summary.students_affected} students affected (${res.impact_summary.new_conflicts} new conflicts, ${res.impact_summary.resolved_conflicts} resolved).`
      );

      await loadData();
    } catch (err: unknown) {
      const msg = getErrorMessage(err, 'Failed to apply timetable change.');
      setStaleError(msg);
    } finally {
      setIsApplyingChange(false);
    }
  };

  const handleCancelProposedChange = () => {
    setImpactModalOpen(false);
    setProposedChange(null);
    setImpactData(null);
    setStaleError(null);
  };

  // Transform meetings into TimeBlock items for CalendarWeekView (reflects proposed move in Change Preview mode)
  const calendarBlocks: TimeBlock[] = useMemo(() => {
    return meetings.map((m) => {
      const isThisProposed = proposedChange && proposedChange.meeting.id === m.id;
      const effectiveDay = isThisProposed ? proposedChange.proposal.day_of_week : m.day_of_week;
      const effectiveStart = isThisProposed ? proposedChange.proposal.start_time.substring(0, 5) : m.start_time.substring(0, 5);
      const effectiveEnd = isThisProposed ? proposedChange.proposal.end_time.substring(0, 5) : m.end_time.substring(0, 5);

      const courseTitle = m.course_name ? `${m.course_code}: ${m.course_name}` : m.course_code || 'Class';
      const sectionLabel = m.section_code ? `Sec ${m.section_code}` : '';
      const roomLabel = m.room_number ? `Rm ${m.room_number}` : 'No room';
      const facultyLabel = m.faculty_name ? `• ${m.faculty_name}` : '';

      return {
        id: m.id,
        day: effectiveDay,
        startTime: effectiveStart,
        endTime: effectiveEnd,
        type: 'class',
        eventSource: 'class',
        label: isThisProposed ? `[PROPOSED] ${courseTitle} (${sectionLabel})` : `${courseTitle} (${sectionLabel})`,
        courseCode: m.course_code || undefined,
        subLabel: isThisProposed ? `Proposed Move • Click to Review Impact` : `${roomLabel} ${facultyLabel}`.trim(),
        repeatsWeekly: true,
      };
    });
  }, [meetings, proposedChange]);

  // Filtered meetings for list view
  const filteredMeetings = useMemo(() => {
    return meetings.filter((m) => {
      if (filterDay !== 'all' && m.day_of_week !== Number(filterDay)) return false;
      if (filterRoom !== 'all' && m.room_id !== Number(filterRoom)) return false;
      return true;
    });
  }, [meetings, filterDay, filterRoom]);

  // Selected section details in meeting form for capacity checking
  const selectedSection = useMemo(() => {
    return sections.find((s) => s.id === Number(meetingForm.section_id));
  }, [sections, meetingForm.section_id]);

  // Selected room details in meeting form for capacity checking
  const selectedRoom = useMemo(() => {
    if (!meetingForm.room_id) return null;
    return rooms.find((r) => r.id === Number(meetingForm.room_id));
  }, [rooms, meetingForm.room_id]);

  const capacityWarning = useMemo(() => {
    if (selectedSection && selectedRoom && selectedRoom.capacity < selectedSection.capacity) {
      return `Room capacity (${selectedRoom.capacity}) is smaller than section capacity (${selectedSection.capacity}).`;
    }
    return null;
  }, [selectedSection, selectedRoom]);

  // Open Create Meeting Modal
  const openCreateMeetingModal = () => {
    setEditingMeeting(null);
    setMeetingForm({
      section_id: sections[0]?.id || 0,
      day_of_week: 1,
      start_time: '09:00',
      end_time: '10:15',
      room_id: rooms[0]?.id || undefined,
      faculty_id: undefined,
      meeting_type: 'lecture',
      status: 'scheduled',
    });
    setMeetingError(null);
    setMeetingModalOpen(true);
  };

  // Open Edit Meeting Modal
  const openEditMeetingModal = (meeting: CourseMeeting) => {
    setEditingMeeting(meeting);
    setMeetingForm({
      section_id: meeting.section_id,
      day_of_week: meeting.day_of_week,
      start_time: meeting.start_time.substring(0, 5),
      end_time: meeting.end_time.substring(0, 5),
      room_id: meeting.room_id || undefined,
      faculty_id: meeting.faculty_id || undefined,
      meeting_type: meeting.meeting_type || 'lecture',
      status: meeting.status || 'scheduled',
    });
    setMeetingError(null);
    setMeetingModalOpen(true);
  };

  // Handle meeting form submit
  const handleSaveMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !timetable) return;

    // Basic client validation
    if (!meetingForm.section_id) {
      setMeetingError('Please select a course section.');
      return;
    }
    if (meetingForm.start_time >= meetingForm.end_time) {
      setMeetingError('Start time must be earlier than end time.');
      return;
    }

    try {
      setSubmittingMeeting(true);
      setMeetingError(null);

      const payload: CourseMeetingCreatePayload = {
        section_id: Number(meetingForm.section_id),
        day_of_week: Number(meetingForm.day_of_week),
        start_time: meetingForm.start_time,
        end_time: meetingForm.end_time,
        room_id: meetingForm.room_id ? Number(meetingForm.room_id) : undefined,
        faculty_id: meetingForm.faculty_id ? Number(meetingForm.faculty_id) : undefined,
        meeting_type: meetingForm.meeting_type || 'lecture',
        status: meetingForm.status || 'scheduled',
      };

      if (editingMeeting) {
        await api.updateMeeting(institution.id, timetable.id, editingMeeting.id, payload as CourseMeetingUpdatePayload);
      } else {
        await api.createMeeting(institution.id, timetable.id, payload);
      }

      setMeetingModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setMeetingError(getErrorMessage(err, 'Failed to save meeting schedule.'));
    } finally {
      setSubmittingMeeting(false);
    }
  };

  // Handle meeting deletion
  const handleDeleteMeeting = async (meetingId: number) => {
    if (!institution || !timetable) return;
    if (!confirm('Are you sure you want to remove this scheduled meeting?')) return;
    try {
      await api.deleteMeeting(institution.id, timetable.id, meetingId);
      await loadData();
    } catch (err: unknown) {
      alert(getErrorMessage(err, 'Failed to delete meeting'));
    }
  };

  // Handle Timetable status update
  const handleStatusChange = async (newStatus: 'draft' | 'active' | 'archived') => {
    if (!institution || !timetable || timetable.status === newStatus) return;
    try {
      await api.updateTimetable(institution.id, timetable.id, { status: newStatus });
      await loadData();
    } catch (err: unknown) {
      alert(getErrorMessage(err, 'Failed to update timetable status'));
    }
  };

  // Handle Timetable details edit
  const handleSaveTimetableDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institution || !timetable) return;
    try {
      setSubmittingTt(true);
      await api.updateTimetable(institution.id, timetable.id, {
        name: ttName.trim(),
        description: ttDescription.trim() || undefined,
      });
      setEditTimetableOpen(false);
      await loadData();
    } catch (err: unknown) {
      alert(getErrorMessage(err, 'Failed to update timetable details'));
    } finally {
      setSubmittingTt(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error || !timetable) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl text-red-200">
        <h3 className="text-lg font-semibold mb-2">Error</h3>
        <p className="mb-4">{error || 'Timetable not found'}</p>
        <Link
          href="/university/timetables"
          className="inline-flex items-center px-4 py-2 bg-red-800 hover:bg-red-700 text-white rounded-lg text-sm transition-colors"
        >
          ← Back to Timetables
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            href="/university/timetables"
            className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-2"
          >
            ← Back to Timetables
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">{timetable.name}</h1>
            <span
              className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
                timetable.status === 'active'
                  ? 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30'
                  : timetable.status === 'draft'
                  ? 'bg-amber-50 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30'
                  : 'bg-slate-100 dark:bg-slate-500/20 text-slate-700 dark:text-slate-400 border border-slate-200 dark:border-slate-500/30'
              }`}
            >
              {timetable.status.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            {timetable.term_name || 'Academic Term'} • Timezone: {institution?.timezone || 'UTC'}
            {timetable.description && ` • ${timetable.description}`}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {isAdmin && (
            <>
              {timetable.status !== 'active' && (
                <button
                  onClick={() => handleStatusChange('active')}
                  className="px-3 py-2 bg-emerald-50 dark:bg-emerald-600/20 border border-emerald-200 dark:border-emerald-500/40 hover:bg-emerald-100 dark:hover:bg-emerald-600/30 text-emerald-700 dark:text-emerald-300 rounded-lg text-sm font-medium transition-all cursor-pointer"
                >
                  ✓ Set as Active Baseline
                </button>
              )}
              {timetable.status === 'active' && (
                <button
                  onClick={() => handleStatusChange('archived')}
                  className="px-3 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-sm font-medium transition-all cursor-pointer"
                >
                  Archive
                </button>
              )}
              <button
                onClick={() => setEditTimetableOpen(true)}
                className="px-3 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              >
                Edit Info
              </button>
              <button
                onClick={() => setPublishModalOpen(true)}
                className="px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-sm font-semibold shadow-md hover:shadow-emerald-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
                title="Publish official version and notify affected students"
              >
                <span>📢</span> Publish Timetable
              </button>
              <button
                onClick={openCreateMeetingModal}
                className="px-4 py-2 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white rounded-lg text-sm font-medium shadow-md hover:shadow-indigo-500/25 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <span>+</span> Add Meeting
              </button>
            </>
          )}
        </div>
      </div>

      {/* Success Notification Banner */}
      {successNotice && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/40 rounded-xl flex items-center justify-between gap-3 text-emerald-900 dark:text-emerald-200 text-sm animate-in fade-in">
          <div className="flex items-center gap-2.5">
            <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
              ✓
            </span>
            <span>{successNotice}</span>
          </div>
          <button
            onClick={() => setSuccessNotice(null)}
            className="text-emerald-700 hover:text-emerald-950 dark:text-emerald-400 dark:hover:text-white text-xs px-2 py-1 rounded hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Change Preview Mode Banner */}
      {proposedChange && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-500/50 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 text-amber-900 dark:text-amber-200 text-sm animate-in fade-in shadow-md">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 text-xs font-bold uppercase tracking-wider rounded-md bg-amber-500 text-slate-950 shadow-sm shrink-0">
              Change Preview
            </span>
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">
                Proposed move: {proposedChange.meeting.course_code || 'Class'} to{' '}
                {DAYS_OF_WEEK.find((d) => d.value === proposedChange.proposal.day_of_week)?.label}{' '}
                {proposedChange.proposal.start_time}–{proposedChange.proposal.end_time}
              </p>
              <p className="text-xs text-amber-800 dark:text-amber-300/80">
                Official timetable remains unchanged until explicitly confirmed.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setImpactModalOpen(true)}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 font-bold rounded-lg text-xs shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span>🔍</span> Review Impact & Apply
            </button>
            <button
              onClick={handleCancelProposedChange}
              className="px-3 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-lg text-xs transition-colors cursor-pointer"
            >
              Discard Move
            </button>
          </div>
        </div>
      )}

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-xs">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Total Meetings</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{meetings.length}</p>
        </div>
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-xs">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Sections Scheduled</p>
          <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-400 mt-1">
            {new Set(meetings.map((m) => m.section_id)).size}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-xs">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Rooms Utilized</p>
          <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-1">
            {new Set(meetings.filter((m) => m.room_id).map((m) => m.room_id)).size}
          </p>
        </div>
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-xs">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold">Faculty Assigned</p>
          <p className="text-2xl font-bold text-amber-700 dark:text-amber-400 mt-1">
            {new Set(meetings.filter((m) => m.faculty_id).map((m) => m.faculty_id)).size}
          </p>
        </div>
      </div>

      {/* View Switcher & Quick Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('calendar')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              viewMode === 'calendar'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            📅 Weekly Grid
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              viewMode === 'list'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            📋 List View ({meetings.length})
          </button>
        </div>

        {viewMode === 'list' && (
          <div className="flex flex-wrap items-center gap-2">
            <div className="w-36">
              <CustomSelect
                options={[
                  { value: 'all', label: 'All Days' },
                  ...DAYS_OF_WEEK.map((d) => ({
                    value: String(d.value),
                    label: d.label,
                  })),
                ]}
                value={filterDay}
                onChange={(val) => setFilterDay(String(val))}
                size="sm"
                portalTheme="university"
              />
            </div>
            <div className="w-48">
              <CustomSelect
                options={[
                  { value: 'all', label: 'All Rooms' },
                  ...rooms.map((r) => ({
                    value: String(r.id),
                    label: `${r.building ? `${r.building} - ` : ''}Room ${r.room_number}`,
                  })),
                ]}
                value={filterRoom}
                onChange={(val) => setFilterRoom(String(val))}
                size="sm"
                portalTheme="university"
              />
            </div>
          </div>
        )}
      </div>

      {/* Main View Area */}
      {viewMode === 'calendar' ? (
        <div className="bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-4 overflow-hidden shadow-xs">
          <div className="mb-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Weekly Schedule Matrix (Click a class block to view details or edit)</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500 inline-block"></span>
                Official Course Meeting
              </span>
            </div>
          </div>
          <CalendarWeekView
            blocks={calendarBlocks}
            startHour={8}
            endHour={20}
            days={['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']}
            onBlockClick={(block) => {
              const mtg = meetings.find((m) => m.id === Number(block.id));
              if (mtg && isAdmin) {
                if (proposedChange && proposedChange.meeting.id === mtg.id) {
                  setImpactModalOpen(true);
                } else {
                  openEditMeetingModal(mtg);
                }
              }
            }}
            onBlockMove={(blockId, newStartTime, newEndTime, newDay) => {
              if (!isAdmin) return;
              const mtg = meetings.find((m) => m.id === Number(blockId));
              if (!mtg) return;

              const targetDay = newDay !== undefined ? (DAY_NAME_TO_INT[newDay] ?? mtg.day_of_week) : mtg.day_of_week;
              triggerPreviewChange(mtg, {
                meeting_id: mtg.id,
                day_of_week: targetDay,
                start_time: newStartTime,
                end_time: newEndTime,
                room_id: mtg.room_id,
                faculty_id: mtg.faculty_id,
                meeting_type: mtg.meeting_type,
              });
            }}
            onBlockResize={(blockId, newEndTime) => {
              if (!isAdmin) return;
              const mtg = meetings.find((m) => m.id === Number(blockId));
              if (!mtg) return;

              triggerPreviewChange(mtg, {
                meeting_id: mtg.id,
                day_of_week: mtg.day_of_week,
                start_time: mtg.start_time.substring(0, 5),
                end_time: newEndTime,
                room_id: mtg.room_id,
                faculty_id: mtg.faculty_id,
                meeting_type: mtg.meeting_type,
              });
            }}
          />
        </div>
      ) : (
        /* List View */
        <div className="bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          {filteredMeetings.length === 0 ? (
            <div className="p-8 text-center text-slate-500 dark:text-slate-400">
              <p className="text-base font-medium">No meetings match current filters</p>
              <p className="text-sm text-slate-500 mt-1">Add meetings or adjust day/room filters above.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    <th className="px-4 py-3">Course & Section</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Day</th>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Room</th>
                    <th className="px-4 py-3">Faculty</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-sm">
                  {filteredMeetings.map((m) => {
                    const dayObj = DAYS_OF_WEEK.find((d) => d.value === m.day_of_week);
                    return (
                      <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-indigo-700 dark:text-indigo-400">{m.course_code || 'Course'}</span>
                            <span className="px-1.5 py-0.5 text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded font-medium">
                              Sec {m.section_code || m.section_id}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{m.course_name}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 text-xs rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 capitalize font-medium">
                            {m.meeting_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{dayObj?.label || m.day_of_week}</td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">
                          {m.start_time.substring(0, 5)} – {m.end_time.substring(0, 5)}
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {m.room_number ? (
                            <div>
                              <span>Rm {m.room_number}</span>
                              {m.room_capacity && (
                                <span className="text-xs text-slate-500 ml-1.5">(Cap: {m.room_capacity})</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 dark:text-slate-500 italic">Unassigned</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {m.faculty_name || <span className="text-slate-400 dark:text-slate-500 italic">Unassigned</span>}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {isAdmin && (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => openEditMeetingModal(m)}
                                className="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded transition-colors cursor-pointer"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteMeeting(m.id)}
                                className="px-2.5 py-1 text-xs bg-red-50 hover:bg-red-100 dark:bg-red-950/40 dark:hover:bg-red-900/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800/40 rounded transition-colors cursor-pointer"
                              >
                                Remove
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Meeting Create / Edit Modal */}
      {meetingModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                {editingMeeting ? 'Edit Scheduled Meeting' : 'Schedule New Course Meeting'}
              </h2>
              <button
                onClick={() => setMeetingModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveMeeting} className="p-6 space-y-4">
              {meetingError && (
                <div className="p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800/80 rounded-xl text-red-700 dark:text-red-200 text-xs leading-relaxed font-medium">
                  ⚠️ {meetingError}
                </div>
              )}

              {/* Section Select */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Academic Section *
                </label>
                <CustomSelect
                  options={sections.map((s) => ({
                    value: String(s.id),
                    label: `${s.course_code ? `${s.course_code} - ` : ''}Sec ${s.section_code} (Cap: ${s.capacity || 'N/A'})`,
                  }))}
                  value={meetingForm.section_id ? String(meetingForm.section_id) : ''}
                  onChange={(val) => setMeetingForm({ ...meetingForm, section_id: Number(val) })}
                  placeholder="Select an offering section..."
                  searchable
                  portalTheme="university"
                />
                {selectedSection && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Section Capacity: {selectedSection.capacity}
                  </p>
                )}
              </div>

              {/* Day and Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Day of Week *
                  </label>
                  <CustomSelect
                    options={DAYS_OF_WEEK.map((d) => ({
                      value: String(d.value),
                      label: d.label,
                    }))}
                    value={String(meetingForm.day_of_week)}
                    onChange={(val) => setMeetingForm({ ...meetingForm, day_of_week: Number(val) })}
                    portalTheme="university"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Meeting Type
                  </label>
                  <CustomSelect
                    options={MEETING_TYPES.map((t) => ({
                      value: t.value,
                      label: t.label,
                    }))}
                    value={meetingForm.meeting_type}
                    onChange={(val) => setMeetingForm({ ...meetingForm, meeting_type: String(val) })}
                    portalTheme="university"
                  />
                </div>
              </div>

              {/* Start & End Time */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Start Time *
                  </label>
                  <input
                    type="time"
                    value={meetingForm.start_time}
                    onChange={(e) => setMeetingForm({ ...meetingForm, start_time: e.target.value })}
                    className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 font-mono"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    End Time *
                  </label>
                  <input
                    type="time"
                    value={meetingForm.end_time}
                    onChange={(e) => setMeetingForm({ ...meetingForm, end_time: e.target.value })}
                    className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 font-mono"
                    required
                  />
                </div>
              </div>

              {/* Room Select */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                    Room Assignment
                  </label>
                  {capacityWarning && (
                    <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">⚠️ {capacityWarning}</span>
                  )}
                </div>
                <CustomSelect
                  options={[
                    { value: '', label: 'No Room Assigned (Unscheduled Room)' },
                    ...rooms.map((r) => ({
                      value: String(r.id),
                      label: `${r.building ? `${r.building} - ` : ''}Room ${r.room_number} (Capacity: ${r.capacity})`,
                    })),
                  ]}
                  value={meetingForm.room_id ? String(meetingForm.room_id) : ''}
                  onChange={(val) =>
                    setMeetingForm({
                      ...meetingForm,
                      room_id: val ? Number(val) : undefined,
                    })
                  }
                  searchable
                  portalTheme="university"
                />
              </div>

              {/* Faculty Override Select */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Faculty Instructor (Optional Override)
                </label>
                <CustomSelect
                  options={[
                    { value: '', label: 'Default to Section Instructor Assignment' },
                    ...facultyList.map((f) => ({
                      value: String(f.id),
                      label: `${f.title ? `${f.title} ` : ''}${f.user_name || `Faculty #${f.id}`} ${f.user_email ? `(${f.user_email})` : ''}`,
                    })),
                  ]}
                  value={meetingForm.faculty_id ? String(meetingForm.faculty_id) : ''}
                  onChange={(val) =>
                    setMeetingForm({
                      ...meetingForm,
                      faculty_id: val ? Number(val) : undefined,
                    })
                  }
                  searchable
                  portalTheme="university"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setMeetingModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                {editingMeeting && (
                  <button
                    type="button"
                    onClick={() => {
                      const proposal: TimetableChangeProposal = {
                        meeting_id: editingMeeting.id,
                        day_of_week: Number(meetingForm.day_of_week),
                        start_time: meetingForm.start_time,
                        end_time: meetingForm.end_time,
                        room_id: meetingForm.room_id ? Number(meetingForm.room_id) : undefined,
                        faculty_id: meetingForm.faculty_id ? Number(meetingForm.faculty_id) : undefined,
                        meeting_type: meetingForm.meeting_type,
                      };
                      setMeetingModalOpen(false);
                      triggerPreviewChange(editingMeeting, proposal);
                    }}
                    className="px-4 py-2 bg-amber-50 dark:bg-amber-600/20 border border-amber-200 dark:border-amber-500/40 hover:bg-amber-100 dark:hover:bg-amber-600/30 text-amber-800 dark:text-amber-300 rounded-xl text-sm font-medium transition-colors cursor-pointer"
                  >
                    🔍 Preview Impact
                  </button>
                )}
                <button
                  type="submit"
                  disabled={submittingMeeting}
                  className="px-5 py-2 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white rounded-xl text-sm font-medium shadow-md transition-all disabled:opacity-50 cursor-pointer"
                >
                  {submittingMeeting ? 'Validating & Saving...' : editingMeeting ? 'Update Meeting' : 'Schedule Meeting'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Timetable Details Modal */}
      {editTimetableOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Edit Timetable Information</h2>
              <button
                onClick={() => setEditTimetableOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveTimetableDetails} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Timetable Name *
                </label>
                <input
                  type="text"
                  value={ttName}
                  onChange={(e) => setTtName(e.target.value)}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Description
                </label>
                <textarea
                  value={ttDescription}
                  onChange={(e) => setTtDescription(e.target.value)}
                  rows={3}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditTimetableOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingTt}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium shadow-md transition-all disabled:opacity-50 cursor-pointer"
                >
                  {submittingTt ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Task N6: Timetable Impact Analysis Modal */}
      <TimetableImpactModal
        isOpen={impactModalOpen}
        isLoading={isImpactLoading}
        impactData={impactData}
        staleError={staleError}
        isApplying={isApplyingChange}
        onApply={handleApplyProposedChange}
        onCancel={handleCancelProposedChange}
        onRefresh={async () => {
          await loadData();
          if (proposedChange) {
            const freshMtg = meetings.find((m) => m.id === proposedChange.meeting.id);
            if (freshMtg) {
              triggerPreviewChange(freshMtg, proposedChange.proposal);
            } else {
              handleCancelProposedChange();
            }
          }
        }}
      />

      {/* Task N8 / N7: Timetable Publish & Automatic Student Notifications */}
      {timetable && institution && (
        <TimetablePublishModal
          isOpen={publishModalOpen}
          onClose={() => setPublishModalOpen(false)}
          institutionId={institution.id}
          timetableId={timetable.id}
          timetableName={timetable.name}
          onPublished={async (summary?: PublishVersionResponse) => {
            await loadData();
            if (summary?.published_version) {
              const students = summary.notification_summary?.students_affected ?? 0;
              const conflicts = summary.notification_summary?.new_conflicts ?? 0;
              setSuccessNotice(
                `Timetable published! Version ${summary.published_version.version_number} is now official. ` +
                `${students} students notified (${conflicts} new conflicts detected).`
              );
            } else {
              setSuccessNotice('Timetable published successfully!');
            }
          }}
        />
      )}
    </div>
  );
}

