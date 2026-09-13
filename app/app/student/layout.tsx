'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';
import { api, UserInstitutionStatus, StudentProfile, Institution, InstitutionMembership } from '@/lib/api';

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

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
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

  const navTabs = [
    { label: 'Courses & Enrollments', href: '/student/academics', icon: '📚' },
    { label: 'Weekly Availability', href: '/student/availability', icon: '🕒' },
    { label: 'Constraints & Preferences', href: '/student/constraints', icon: '⚖️' },
  ];

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors">
        <Navbar />

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
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
            {/* Header / Sub-Nav Bar */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">🎓</span>
                    <h1 className="text-xl font-black tracking-tight text-[var(--text-primary)]">
                      My Academic Courses
                    </h1>
                    {institution && (
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {institution.name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-indigo-400 font-medium mt-1">
                    Plan classes, work, and life in one schedule.
                  </p>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                    Manage your enrolled university course sections, weekly availability, and scheduling preferences.
                  </p>
                </div>

                {/* Sub-Navigation Tabs */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
                  {navTabs.map((tab) => {
                    const isActive = pathname === tab.href;
                    return (
                      <Link
                        key={tab.href}
                        href={tab.href}
                        className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition flex items-center gap-1.5 ${
                          isActive
                            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/20'
                            : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                        }`}
                      >
                        <span>{tab.icon}</span>
                        <span>{tab.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* If user is not associated with an institution */}
            {!loading && !institution && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-start gap-3">
                <span className="text-xl">⚠️</span>
                <div className="text-xs space-y-1">
                  <div className="font-bold text-amber-300">No University Institution Linked</div>
                  <p className="text-amber-200/80">
                    Your account is not currently registered as a student in an active institution. Institutional course enrollment and university timetabling require an institutional membership. You can create or join an institution in the{' '}
                    <Link href="/university" className="underline font-semibold text-amber-200 hover:text-white">
                      University Portal
                    </Link>.
                  </p>
                </div>
              </div>
            )}

            {/* Main Content Area */}
            {children}
          </div>
        </StudentContext.Provider>
      </div>
    </ProtectedRoute>
  );
}
