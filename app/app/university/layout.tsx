'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import RoleGuard from '@/components/RoleGuard';
import { SidebarNavItem } from '@/components/ui/PortalSidebar';
import AppShell from '@/components/unified/AppShell';
import Link from 'next/link';
import { api, UserInstitutionStatus, Institution, InstitutionMembership } from '@/lib/api';
import {
  BuildingLibraryIcon,
  CalendarDaysIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  AcademicCapIcon,
  UsersIcon,
  BuildingOfficeIcon,
  BuildingOffice2Icon,
  BoltIcon,
  ChartBarIcon,
  BellIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';

// ── University Context ─────────────────────────────────────────────────────

interface UniversityContextType {
  status: UserInstitutionStatus | null;
  loading: boolean;
  refresh: () => Promise<void>;
  institution: Institution | null;
  membership: InstitutionMembership | null;
  isAdmin: boolean;
  isSuperAdmin: boolean;
}

const UniversityContext = createContext<UniversityContextType>({
  status: null,
  loading: true,
  refresh: async () => {},
  institution: null,
  membership: null,
  isAdmin: false,
  isSuperAdmin: false,
});

export function useUniversity() {
  return useContext(UniversityContext);
}

// ── University Navigation Items ────────────────────────────────────────────

const universityNavItems: SidebarNavItem[] = [
  { label: 'Dashboard', href: '/university/dashboard', icon: <BuildingLibraryIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Timetables', href: '/university/timetables', icon: <CalendarDaysIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Courses', href: '/university/courses', icon: <BookOpenIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Sections', href: '/university/sections', icon: <ClipboardDocumentListIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Faculty', href: '/university/faculty', icon: <AcademicCapIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Students', href: '/university/students', icon: <UsersIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Rooms', href: '/university/rooms', icon: <BuildingOfficeIcon className="w-5 h-5" aria-hidden="true" />, adminOnly: true },
  { label: 'Departments', href: '/university/departments', icon: <BuildingOffice2Icon className="w-5 h-5" aria-hidden="true" />, adminOnly: true },
  { label: 'Academic Terms', href: '/university/terms', icon: <CalendarDaysIcon className="w-5 h-5" aria-hidden="true" />, adminOnly: true },
  { label: 'Impact Analysis', href: '/university/impact-analysis', icon: <BoltIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Analytics', href: '/university/analytics', icon: <ChartBarIcon className="w-5 h-5" aria-hidden="true" />, adminOnly: true },
  { label: 'Notifications', href: '/university/notifications', icon: <BellIcon className="w-5 h-5" aria-hidden="true" /> },
  { label: 'Audit Logs', href: '/university/audit-logs', icon: <DocumentTextIcon className="w-5 h-5" aria-hidden="true" />, superAdminOnly: true },
  { label: 'Settings', href: '/university/settings', icon: <Cog6ToothIcon className="w-5 h-5" aria-hidden="true" />, superAdminOnly: true },
];

// ── Layout Component ───────────────────────────────────────────────────────

export default function UniversityLayout({ children }: { children: React.ReactNode }) {
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
        if (!cancelled) setStatus(data);
      } catch {
        if (!cancelled) {
          setStatus({ has_institution: false, institution: null, membership: null });
        }
      } finally {
        if (!cancelled) setLoading(false);
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
  const isSuperAdmin = membership?.role === 'super_admin';

  return (
    <ProtectedRoute>
      <RoleGuard allowedPortal="university">
        <UniversityContext.Provider
          value={{
            status,
            loading,
            refresh: loadStatus,
            institution,
            membership,
            isAdmin,
            isSuperAdmin,
          }}
        >
          <AppShell>
            {isSuperAdmin && (
              <div className="bg-indigo-50 dark:bg-indigo-900/30 border-b border-indigo-100 dark:border-indigo-800/50 px-6 py-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">Super Admin Mode</span>
                <Link className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline" href="/admin">Open Legacy Super-Admin Portal →</Link>
              </div>
            )}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              {children}
            </div>
          </AppShell>
        </UniversityContext.Provider>
      </RoleGuard>
    </ProtectedRoute>
  );
}
