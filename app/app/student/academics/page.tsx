'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useStudentAcademic } from '../layout';
import Link from 'next/link';
import {
  api,
  getErrorMessage,
  SectionEnrollment,
  AvailableSection,
  AcademicTerm,
  Department,
  StudentProfileUpdatePayload,
  CourseMeeting,
} from '@/lib/api';
import { showSuccessToast, showErrorToast } from '@/lib/toast';
import CustomSelect from '@/components/ui/CustomSelect';

export default function StudentAcademicsPage() {
  const { institution, profile, refresh: refreshProfile } = useStudentAcademic();

  // Active view: 'enrolled' vs 'catalog'
  const [activeTab, setActiveTab] = useState<'enrolled' | 'catalog'>('enrolled');

  // Enrollments state
  const [enrollments, setEnrollments] = useState<SectionEnrollment[]>([]);
  const [scheduledMeetings, setScheduledMeetings] = useState<Record<number, CourseMeeting[]>>({});
  const [loadingEnrollments, setLoadingEnrollments] = useState(true);

  // Available sections catalog state
  const [availableSections, setAvailableSections] = useState<AvailableSection[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(false);

  // Filters
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedTermId, setSelectedTermId] = useState<number | undefined>(undefined);
  const [selectedDeptId, setSelectedDeptId] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');

  // Action states
  const [enrollingSectionId, setEnrollingSectionId] = useState<number | null>(null);
  const [droppingEnrollmentId, setDroppingEnrollmentId] = useState<number | null>(null);
  const [dropConfirmModal, setDropConfirmModal] = useState<SectionEnrollment | null>(null);

  // Profile Edit modal
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileForm, setProfileForm] = useState<StudentProfileUpdatePayload>({
    student_number: '',
    program: '',
    year_of_study: 1,
    department_id: null,
  });
  const [savingProfile, setSavingProfile] = useState(false);

  // Load terms and departments for filters
  useEffect(() => {
    if (!institution) return;
    async function loadMeta() {
      try {
        const [termsData, deptsData] = await Promise.all([
          api.getAcademicTerms(institution!.id),
          api.getDepartments(institution!.id),
        ]);
        setTerms(termsData.filter((t) => t.status === 'active' || t.status === 'upcoming'));
        setDepartments(deptsData.filter((d) => d.is_active));
      } catch {
        // Fallback silently
      }
    }
    loadMeta();
  }, [institution]);

  // Sync profile form when profile loads
  useEffect(() => {
    if (profile) {
      setProfileForm({
        student_number: profile.student_number || '',
        program: profile.program || '',
        year_of_study: profile.year_of_study || 1,
        department_id: profile.department_id || null,
      });
    }
  }, [profile]);

  // Load enrollments and authoritative meeting schedules
  const fetchEnrollments = useCallback(async () => {
    try {
      setLoadingEnrollments(true);
      const [enrollmentData, scheduleData] = await Promise.all([
        api.getMyEnrollments({
          academic_term_id: selectedTermId,
          status: 'active',
        }),
        api.getMyAcademicSchedule({ term_id: selectedTermId }).catch(() => null),
      ]);
      setEnrollments(enrollmentData);

      if (scheduleData && scheduleData.meetings) {
        const bySec: Record<number, CourseMeeting[]> = {};
        for (const m of scheduleData.meetings) {
          if (!bySec[m.section_id]) bySec[m.section_id] = [];
          bySec[m.section_id].push(m);
        }
        setScheduledMeetings(bySec);
      } else {
        setScheduledMeetings({});
      }
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to load enrollments'));
    } finally {
      setLoadingEnrollments(false);
    }
  }, [selectedTermId]);

  // Load available catalog
  const fetchCatalog = useCallback(async () => {
    if (!institution) return;
    try {
      setLoadingCatalog(true);
      const data = await api.getAvailableSections(institution.id, {
        academic_term_id: selectedTermId,
        department_id: selectedDeptId,
        search: searchQuery.trim() || undefined,
      });
      setAvailableSections(data);
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to load course sections'));
    } finally {
      setLoadingCatalog(false);
    }
  }, [institution, selectedTermId, selectedDeptId, searchQuery]);

  useEffect(() => {
    fetchEnrollments();
  }, [fetchEnrollments]);

  useEffect(() => {
    if (activeTab === 'catalog') {
      fetchCatalog();
    }
  }, [activeTab, fetchCatalog]);

  // Handle Enroll
  const handleEnroll = async (sectionId: number) => {
    try {
      setEnrollingSectionId(sectionId);
      await api.enrollInSection({ section_id: sectionId });
      showSuccessToast('Successfully enrolled in section!');
      await Promise.all([fetchEnrollments(), fetchCatalog()]);
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to enroll in section'));
    } finally {
      setEnrollingSectionId(null);
    }
  };

  // Handle Drop
  const handleConfirmDrop = async () => {
    if (!dropConfirmModal) return;
    try {
      setDroppingEnrollmentId(dropConfirmModal.id);
      await api.dropEnrollment(dropConfirmModal.id);
      showSuccessToast('Enrollment dropped successfully.');
      setDropConfirmModal(null);
      await Promise.all([fetchEnrollments(), fetchCatalog()]);
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to drop enrollment'));
    } finally {
      setDroppingEnrollmentId(null);
    }
  };

  // Handle Save Profile
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingProfile(true);
      await api.updateMyStudentProfile({
        student_number: profileForm.student_number || null,
        program: profileForm.program || null,
        year_of_study: profileForm.year_of_study ? Number(profileForm.year_of_study) : null,
        department_id: profileForm.department_id ? Number(profileForm.department_id) : null,
      });
      showSuccessToast('Academic profile updated!');
      setProfileModalOpen(false);
      await refreshProfile();
    } catch (err) {
      showErrorToast(getErrorMessage(err, 'Failed to update academic profile'));
    } finally {
      setSavingProfile(false);
    }
  };

  // Calculate totals
  const totalCredits = enrollments.reduce((acc, curr) => acc + (curr.credits || 0), 0);

  return (
    <div className="space-y-6">
      {/* 1. Academic Profile Overview Card */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center text-2xl shrink-0">
              🎓
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-[var(--text-primary)]">
                  {profile?.program || 'Academic Student Profile'}
                </h2>
                {profile?.year_of_study && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                    Year {profile.year_of_study}
                  </span>
                )}
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  {profile?.status || 'active'}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {institution?.name || 'No institution'} • {profile?.department_name || 'General Department'}
                {profile?.student_number ? ` • Student ID: ${profile.student_number}` : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setProfileModalOpen(true)}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-primary)] border border-[var(--border-color)] transition flex items-center gap-1.5 cursor-pointer"
            >
              <span>✏️</span>
              <span>Edit Details</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Main View Controls & Sub-tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border-color)] pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('enrolled')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'enrolled'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/20'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
            }`}
          >
            <span>📑</span>
            <span>My Enrolled Sections</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'enrolled'
                  ? 'bg-black/25 text-white'
                  : 'bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]'
              }`}
            >
              {enrollments.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'catalog'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/20'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
            }`}
          >
            <span>🔍</span>
            <span>Browse & Enroll</span>
          </button>
        </div>

        {/* Term filter for both tabs */}
        <div className="flex items-center gap-2 w-48">
          <CustomSelect
            options={[
              { value: '', label: 'All Terms' },
              ...terms.map((t) => ({ value: String(t.id), label: t.name })),
            ]}
            value={selectedTermId ? String(selectedTermId) : ''}
            onChange={(val) => setSelectedTermId(val ? Number(val) : undefined)}
            size="sm"
            portalTheme="student"
          />
        </div>
      </div>

      {/* 3. TAB CONTENT */}
      {activeTab === 'enrolled' && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex items-center justify-between bg-[var(--bg-secondary)]/60 border border-[var(--border-color)] rounded-xl px-4 py-2.5 text-xs text-[var(--text-secondary)]">
            <span>
              Total Registered Credits: <strong className="text-emerald-400 font-bold">{totalCredits}</strong>
            </span>
            <span>
              Enrolled Sections: <strong className="text-indigo-400 font-bold">{enrollments.length}</strong>
            </span>
          </div>

          {loadingEnrollments ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Loading active enrollments...</span>
            </div>
          ) : enrollments.length === 0 ? (
            <div className="bg-[var(--bg-card)] border border-dashed border-[var(--border-color)] rounded-2xl p-10 text-center space-y-3">
              <div className="text-4xl">📚</div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                No Enrolled Course Sections
              </h3>
              <p className="text-xs text-[var(--text-secondary)] max-w-sm mx-auto">
                You haven&apos;t enrolled in any university course sections for this term yet. Browse the catalog to select and enroll in your classes.
              </p>
              <button
                onClick={() => setActiveTab('catalog')}
                className="mt-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow transition cursor-pointer"
              >
                Browse Course Catalog →
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {enrollments.map((enr) => (
                <div
                  key={enr.id}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm hover:border-indigo-500/30 transition flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-[var(--text-primary)] font-mono">
                            {enr.course_code}
                          </span>
                          <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[11px] font-mono">
                            Sec {enr.section_code}
                          </span>
                        </div>
                        <h4 className="text-sm font-semibold text-[var(--text-primary)] mt-0.5">
                          {enr.course_name}
                        </h4>
                      </div>

                      <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20 shrink-0">
                        {enr.credits || 0} Credits
                      </span>
                    </div>

                    <div className="text-xs text-[var(--text-secondary)] space-y-1 pt-1">
                      {enr.term_name && <div>Term: {enr.term_name}</div>}
                      {enr.instructors && enr.instructors.length > 0 && (
                        <div>Instructor: Prof. {enr.instructors.join(', ')}</div>
                      )}
                      <div className="text-[11px] text-slate-400">
                        Enrolled: {new Date(enr.enrollment_date).toLocaleDateString()}
                      </div>
                    </div>

                    {scheduledMeetings[enr.section_id] && scheduledMeetings[enr.section_id].length > 0 && (
                      <div className="mt-2.5 pt-2.5 border-t border-[var(--border-color)]/60">
                        <div className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                          <span>Scheduled Meetings</span>
                          <span className="text-[10px] text-slate-400 font-normal">Official Baseline</span>
                        </div>
                        <div className="space-y-1.5">
                          {scheduledMeetings[enr.section_id].map((m) => (
                            <div
                              key={m.id}
                              className="text-xs bg-indigo-950/40 border border-indigo-500/20 rounded-lg px-2.5 py-1.5 flex items-center justify-between text-indigo-200"
                            >
                              <span className="font-medium">
                                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][m.day_of_week]} {m.start_time.substring(0, 5)}–{m.end_time.substring(0, 5)}
                              </span>
                              <div className="flex items-center gap-2 text-[11px]">
                                {m.room_number ? (
                                  <span className="text-slate-300">Rm {m.room_number}</span>
                                ) : (
                                  <span className="text-slate-500 italic">No room</span>
                                )}
                                <span className="capitalize px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">
                                  {m.meeting_type}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="pt-4 mt-3 border-t border-[var(--border-color)] flex items-center justify-between">
                    <Link
                      href="/student/calendar"
                      className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium transition flex items-center gap-1"
                    >
                      <span>📅 View on Calendar →</span>
                    </Link>
                    <button
                      onClick={() => setDropConfirmModal(enr)}
                      disabled={droppingEnrollmentId === enr.id}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-700 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-300 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 transition cursor-pointer"
                    >
                      Drop Section
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 4. CATALOG TAB */}
      {activeTab === 'catalog' && (
        <div className="space-y-4">
          {/* Catalog Filter Controls */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs">
                🔍
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by course code or title (e.g., CS101, Database)..."
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="w-full sm:w-56">
                <CustomSelect
                  options={[
                    { value: '', label: 'All Departments' },
                    ...departments.map((d) => ({ value: String(d.id), label: d.name })),
                  ]}
                  value={selectedDeptId ? String(selectedDeptId) : ''}
                  onChange={(val) => setSelectedDeptId(val ? Number(val) : undefined)}
                  size="sm"
                  searchable
                  portalTheme="student"
                />
              </div>

              <button
                onClick={fetchCatalog}
                className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition cursor-pointer shrink-0"
              >
                Search
              </button>
            </div>
          </div>

          {/* Catalog Grid */}
          {loadingCatalog ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs">Loading course catalog...</span>
            </div>
          ) : availableSections.length === 0 ? (
            <div className="bg-[var(--bg-card)] border border-dashed border-[var(--border-color)] rounded-2xl p-10 text-center text-xs text-[var(--text-secondary)]">
              No sections match the current search criteria or department filter.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {availableSections.map((sec) => {
                const isEnrolled = sec.is_enrolled;
                const isFull = sec.is_full || sec.remaining_seats <= 0;
                const capacityPct = Math.min(100, Math.round((sec.enrolled_count / (sec.capacity || 1)) * 100));

                return (
                  <div
                    key={sec.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm hover:border-indigo-500/30 transition flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-[var(--text-primary)] font-mono">
                              {sec.course_code}
                            </span>
                            <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-[11px] font-mono border border-slate-700">
                              Sec {sec.section_code}
                            </span>
                          </div>
                          <h4 className="text-sm font-semibold text-[var(--text-primary)] mt-0.5">
                            {sec.course_name}
                          </h4>
                        </div>

                        <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-bold border border-indigo-500/20 shrink-0">
                          {sec.credits} Cr
                        </span>
                      </div>

                      {sec.description && (
                        <p className="text-xs text-[var(--text-secondary)] line-clamp-2">
                          {sec.description}
                        </p>
                      )}

                      <div className="text-xs text-[var(--text-secondary)] space-y-1 pt-1">
                        {sec.term_name && <div>Term: {sec.term_name}</div>}
                        {sec.instructors && sec.instructors.length > 0 && (
                          <div>
                            Instructor:{' '}
                            {sec.instructors.map((i) => i.faculty_name).filter(Boolean).join(', ') || 'TBA'}
                          </div>
                        )}
                      </div>

                      {/* Capacity Progress Bar */}
                      <div className="pt-2">
                        <div className="flex justify-between text-[11px] text-[var(--text-secondary)] mb-1">
                          <span>
                            Capacity: {sec.enrolled_count} / {sec.capacity} enrolled
                          </span>
                          <span className={isFull ? 'text-rose-400 font-bold' : 'text-emerald-400 font-medium'}>
                            {isFull ? 'Full (0 seats)' : `${sec.remaining_seats} seats remaining`}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              isFull ? 'bg-rose-500' : capacityPct > 80 ? 'bg-amber-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${capacityPct}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 mt-3 border-t border-[var(--border-color)] flex items-center justify-between">
                      <span className="text-[11px] text-slate-400">
                        {isEnrolled ? (
                          <span className="text-emerald-400 font-semibold flex items-center gap-1">
                            ✓ Currently Enrolled
                          </span>
                        ) : isFull ? (
                          <span className="text-rose-400 font-semibold">Section Full</span>
                        ) : (
                          <span className="text-slate-400">Open for enrollment</span>
                        )}
                      </span>

                      {isEnrolled ? (
                        <button
                          disabled
                          className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-default"
                        >
                          Enrolled
                        </button>
                      ) : (
                        <button
                          onClick={() => handleEnroll(sec.id)}
                          disabled={isFull || enrollingSectionId === sec.id}
                          className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer ${
                            isFull
                              ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
                              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow hover:shadow-indigo-950/30'
                          }`}
                        >
                          {enrollingSectionId === sec.id ? (
                            <>
                              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                              <span>Enrolling...</span>
                            </>
                          ) : (
                            <span>Enroll</span>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 5. DROP CONFIRMATION MODAL */}
      {dropConfirmModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <span className="text-2xl">⚠️</span>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Drop Section Enrollment
              </h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Are you sure you want to drop your enrollment in{' '}
              <strong className="text-[var(--text-primary)]">
                {dropConfirmModal.course_code} - Sec {dropConfirmModal.section_code}
              </strong>{' '}
              ({dropConfirmModal.course_name})? This will free up your seat for other students.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setDropConfirmModal(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-primary)] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDrop}
                disabled={droppingEnrollmentId !== null}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-lg transition cursor-pointer flex items-center gap-2"
              >
                {droppingEnrollmentId !== null && (
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                <span>Confirm Drop</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. PROFILE EDIT MODAL */}
      {profileModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Edit Academic Profile
              </h3>
              <button
                onClick={() => setProfileModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Student Number / ID
                </label>
                <input
                  type="text"
                  value={profileForm.student_number || ''}
                  onChange={(e) => setProfileForm({ ...profileForm, student_number: e.target.value })}
                  placeholder="e.g., STU-2026-0042"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Degree / Program
                </label>
                <input
                  type="text"
                  value={profileForm.program || ''}
                  onChange={(e) => setProfileForm({ ...profileForm, program: e.target.value })}
                  placeholder="e.g., B.S. Computer Science"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Year of Study
                  </label>
                  <CustomSelect
                    options={[1, 2, 3, 4, 5, 6].map((yr) => ({ value: String(yr), label: `Year ${yr}` }))}
                    value={String(profileForm.year_of_study || 1)}
                    onChange={(val) => setProfileForm({ ...profileForm, year_of_study: Number(val) })}
                    portalTheme="student"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Department
                  </label>
                  <CustomSelect
                    options={[
                      { value: '', label: 'None / Undeclared' },
                      ...departments.map((d) => ({ value: String(d.id), label: d.name })),
                    ]}
                    value={profileForm.department_id ? String(profileForm.department_id) : ''}
                    onChange={(val) =>
                      setProfileForm({
                        ...profileForm,
                        department_id: val ? Number(val) : null,
                      })
                    }
                    searchable
                    portalTheme="student"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-color)]">
                <button
                  type="button"
                  onClick={() => setProfileModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-primary)] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow transition cursor-pointer flex items-center gap-2"
                >
                  {savingProfile && (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  )}
                  <span>Save Profile</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
