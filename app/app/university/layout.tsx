'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import RoleGuard from '@/components/RoleGuard';
import PortalSidebar, { SidebarNavItem } from '@/components/ui/PortalSidebar';
import { api, UserInstitutionStatus, Institution, InstitutionMembership } from '@/lib/api';

// ── University Context ─────────────────────────────────────────────────────

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

// ── University Navigation Items ────────────────────────────────────────────

const universityNavItems: SidebarNavItem[] = [
  { label: 'Dashboard', href: '/university/dashboard', icon: '🏛️' },
  { label: 'Timetables', href: '/university/timetables', icon: '🗓️' },
  { label: 'Courses', href: '/university/courses', icon: '📚' },
  { label: 'Sections', href: '/university/sections', icon: '📋' },
  { label: 'Faculty', href: '/university/faculty', icon: '👨‍🏫' },
  { label: 'Students', href: '/university/students', icon: '👥' },
  { label: 'Rooms', href: '/university/rooms', icon: '🏢', adminOnly: true },
  { label: 'Departments', href: '/university/departments', icon: '🏛️', adminOnly: true },
  { label: 'Academic Terms', href: '/university/terms', icon: '📅', adminOnly: true },
  { label: 'Impact Analysis', href: '/university/impact-analysis', icon: '⚡' },
  { label: 'Analytics', href: '/university/analytics', icon: '📊', adminOnly: true },
  { label: 'Notifications', href: '/university/notifications', icon: '🔔' },
  { label: 'Audit Logs', href: '/university/audit-logs', icon: '📜', adminOnly: true },
  { label: 'Settings', href: '/university/settings', icon: '⚙️', adminOnly: true },
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
          }}
        >
          <PortalSidebar
            portalLabel="University Portal"
            accentColor="emerald"
            navItems={universityNavItems}
            userRole={membership?.role}
            institutionName={institution?.name}
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              {children}
            </div>
          </PortalSidebar>
        </UniversityContext.Provider>
      </RoleGuard>
    </ProtectedRoute>
  );
}
