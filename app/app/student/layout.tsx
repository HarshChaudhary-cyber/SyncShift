'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import RoleGuard from '@/components/RoleGuard';
import PortalSidebar from '@/components/ui/PortalSidebar';
import { api, UserInstitutionStatus, StudentProfile, Institution, InstitutionMembership } from '@/lib/api';

// ── Student Context ────────────────────────────────────────────────────────

interface StudentContextType {
  status: UserInstitutionStatus | null;
  profile: StudentProfile | null;
  loading: boolean;
  refresh: () => Promise<void>;
  institution: Institution | null;
  membership: InstitutionMembership | null;
}

const StudentContext = createContext<StudentContextType>({
  status: null,
  profile: null,
  loading: true,
  refresh: async () => {},
  institution: null,
  membership: null,
});

export function useStudentAcademic() {
  return useContext(StudentContext);
}

// ── Student Navigation Items ───────────────────────────────────────────────

const studentNavItems = [
  { label: 'Dashboard', href: '/student/dashboard', icon: '🏠' },
  { label: 'My Timetable', href: '/student/timetable', icon: '🗓️' },
  { label: 'Calendar', href: '/student/calendar', icon: '📅' },
  { label: 'My Courses', href: '/student/courses', icon: '📚' },
  { label: 'Work Shifts', href: '/student/shifts', icon: '💼' },
  { label: 'Study Tasks', href: '/student/tasks', icon: '📝' },
  { label: 'Smart Planner', href: '/student/planner', icon: '🧠' },
  { label: 'Conflicts', href: '/student/conflicts', icon: '⚠️' },
  { label: 'Notifications', href: '/student/notifications', icon: '🔔' },
  { label: 'Ask SyncShift AI', href: '/student/assistant', icon: '✨' },
  { label: 'Settings', href: '/student/settings', icon: '⚙️' },
];

// ── Layout Component ───────────────────────────────────────────────────────

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<UserInstitutionStatus | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [instStatus, studentProf] = await Promise.allSettled([
        api.getMyInstitutionStatus(),
        api.getMyStudentProfile(),
      ]);

      if (instStatus.status === 'fulfilled') {
        setStatus(instStatus.value);
      } else {
        setStatus({ has_institution: false, institution: null, membership: null });
      }

      if (studentProf.status === 'fulfilled') {
        setProfile(studentProf.value);
      } else {
        setProfile(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const institution = status?.institution || null;
  const membership = status?.membership || null;

  return (
    <ProtectedRoute>
      <RoleGuard allowedPortal="student">
        <StudentContext.Provider
          value={{
            status,
            profile,
            loading,
            refresh: loadData,
            institution,
            membership,
          }}
        >
          <PortalSidebar
            portalLabel="Student Portal"
            accentColor="indigo"
            navItems={studentNavItems}
            userRole={membership?.role || 'student'}
            institutionName={institution?.name}
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              {children}
            </div>
          </PortalSidebar>
        </StudentContext.Provider>
      </RoleGuard>
    </ProtectedRoute>
  );
}
