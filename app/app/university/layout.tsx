'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';
import { api, UserInstitutionStatus, Institution, InstitutionMembership } from '@/lib/api';

interface UniversityContextType {
  status: UserInstitutionStatus | null;
  loading: boolean;
  refresh: () => Promise<void>;
  institution: Institution | null;
  membership: InstitutionMembership | null;
  isAdmin: boolean;
}

const UniversityContext = createContext<UniversityContextType>({
  status: null,
  loading: true,
  refresh: async () => {},
  institution: null,
  membership: null,
  isAdmin: false,
});

export function useUniversity() {
  return useContext(UniversityContext);
}

export default function UniversityLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [status, setStatus] = useState<UserInstitutionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMyInstitutionStatus();
      setStatus(data);
    } catch {
      setStatus({ has_institution: false, institution: null, membership: null });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        setLoading(true);
        const data = await api.getMyInstitutionStatus();
        if (!cancelled) {
          setStatus(data);
        }
      } catch {
        if (!cancelled) {
          setStatus({ has_institution: false, institution: null, membership: null });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const institution = status?.institution || null;
  const membership = status?.membership || null;
  const isAdmin = membership?.role === 'admin' || membership?.role === 'super_admin';

  const isResourcesActive =
    pathname.startsWith('/university/resources') ||
    pathname.startsWith('/university/courses') ||
    pathname.startsWith('/university/sections') ||
    pathname.startsWith('/university/faculty') ||
    pathname.startsWith('/university/rooms') ||
    pathname.startsWith('/university/departments') ||
    pathname.startsWith('/university/terms');

  const navItems = [
    {
      label: 'Home',
      href: '/university',
      icon: '🏛️',
      isActive: pathname === '/university',
    },
    {
      label: 'Timetable',
      href: '/university/timetables',
      icon: '🗓️',
      isActive: pathname.startsWith('/university/timetables'),
    },
    {
      label: 'Academic Resources',
      href: '/university/resources',
      icon: '📚',
      isActive: isResourcesActive,
    },
    ...(isAdmin
      ? [
          {
            label: 'Students',
            href: '/university/members',
            icon: '👥',
            isActive: pathname.startsWith('/university/members'),
          },
        ]
      : []),
  ];

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors">
        <Navbar />

        <UniversityContext.Provider
          value={{
            status,
            loading,
            refresh: loadStatus,
            institution,
            membership,
            isAdmin,
          }}
        >
          {institution && (
            <div className="border-b border-[var(--border-color)] bg-[var(--bg-secondary)] backdrop-blur-sm sticky top-[57px] z-30">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-4 pb-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🏛️</span>
                      <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                        {institution.name}
                      </h1>
                      <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-[var(--bg-elevated)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                        {institution.code}
                      </span>
                    </div>
                    <p className="text-xs text-indigo-400 font-medium mt-1">
                      Build better timetables and understand their impact on students.
                    </p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                      {institution.timezone} • {institution.country || 'Global'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--text-muted)]">Your Role:</span>
                    <span
                      className={`px-2.5 py-1 text-xs font-semibold rounded-full uppercase tracking-wider ${
                        isAdmin
                          ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                          : membership?.role === 'professor'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                      }`}
                    >
                      {membership?.role || 'Student'}
                    </span>
                  </div>
                </div>

                {/* Simplified Conceptual Navigation Tabs */}
                <div className="flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-1 overflow-x-auto no-scrollbar">
                  <div className="flex items-center gap-1 sm:gap-2">
                    {navItems.map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                          item.isActive
                            ? 'border-indigo-500 text-indigo-400 font-semibold'
                            : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
                        }`}
                      >
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    ))}
                  </div>

                  {/* Ask SyncShift Trigger */}
                  <button
                    type="button"
                    onClick={() => openSyncShiftAssistant()}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-500/15 via-purple-500/15 to-pink-500/15 border border-indigo-500/30 text-indigo-300 hover:text-white hover:border-indigo-400 hover:shadow-xs transition whitespace-nowrap cursor-pointer shrink-0 mb-1"
                  >
                    <span>✨</span>
                    <span>Ask SyncShift</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
            {children}
          </main>
        </UniversityContext.Provider>
      </div>
    </ProtectedRoute>
  );
}
