'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';

export type PortalRole = 'student' | 'faculty' | 'professor' | 'admin' | 'super_admin';

interface RoleGuardProps {
  children: React.ReactNode;
  /** The portal this route belongs to */
  allowedPortal: 'student' | 'university';
}

/**
 * Checks if a given role belongs to the University Portal.
 */
export function isUniversityRole(role?: string | null): boolean {
  if (!role) return false;
  const normalized = role.toLowerCase().trim();
  return (
    normalized === 'faculty' ||
    normalized === 'professor' ||
    normalized === 'admin' ||
    normalized === 'super_admin'
  );
}

/**
 * Checks if a given role belongs to the Student Portal.
 */
export function isStudentRole(role?: string | null): boolean {
  if (!role) return true; // Default unassigned users to student portal
  const normalized = role.toLowerCase().trim();
  return normalized === 'student';
}

/**
 * Role-based route guard.
 *
 * Enforces strict portal separation:
 * - Student Portal (/student/*): ONLY accessible to students (and users with no institution role).
 *   Faculty/Admin accounts are redirected to /university/dashboard.
 * - University Portal (/university/*): ONLY accessible to faculty, professors, and administrators.
 *   Students are strictly denied access and redirected to /student/dashboard.
 */
export default function RoleGuard({ children, allowedPortal }: RoleGuardProps) {
  const { status, user } = useAuthContext();
  const router = useRouter();

  const role = user?.institution_role;
  const hasUniversityRole = isUniversityRole(role);

  useEffect(() => {
    if (status !== 'authenticated' || !user) return;

    if (allowedPortal === 'university' && !hasUniversityRole) {
      // Student trying to access university portal → redirect to student dashboard
      router.replace('/student/dashboard');
    } else if (allowedPortal === 'student' && hasUniversityRole) {
      // University user trying to access student portal → redirect to university dashboard
      router.replace('/university/dashboard');
    }
  }, [status, user, allowedPortal, hasUniversityRole, router]);

  // If session is still verifying, show loading
  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // If student attempts to access university portal, DO NOT render children.
  // Show 403 access restriction and redirect to student dashboard.
  if (allowedPortal === 'university' && !hasUniversityRole) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8 shadow-2xl space-y-4 animate-in fade-in duration-200">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center text-3xl">
            🔒
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Access Denied (403)</h2>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              The University Portal is restricted to authorized faculty and university administrators. Students may only access the Student Portal.
            </p>
          </div>
          <div className="pt-2">
            <button
              onClick={() => router.replace('/student/dashboard')}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition cursor-pointer shadow-lg shadow-indigo-950/30"
            >
              ← Return to Student Portal
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If university user attempts to access student portal, block and redirect to university portal
  if (allowedPortal === 'student' && hasUniversityRole) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8 shadow-2xl space-y-4 animate-in fade-in duration-200">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-3xl">
            🏛️
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">University Account Detected</h2>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              You are logged in with an institutional faculty/admin account. Redirecting to your University Portal…
            </p>
          </div>
          <div className="pt-2">
            <button
              onClick={() => router.replace('/university/dashboard')}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition cursor-pointer shadow-lg shadow-emerald-950/30"
            >
              Go to University Portal →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Authorized portal access
  return <>{children}</>;
}

/**
 * Helper to determine which portal a user should be redirected to after login.
 */
export function getPortalRedirect(institutionRole?: string | null): string {
  if (isUniversityRole(institutionRole)) {
    return '/university/dashboard';
  }
  return '/student/dashboard';
}
