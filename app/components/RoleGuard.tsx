'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';

export type PortalRole = 'student' | 'faculty' | 'professor' | 'admin' | 'super_admin';
export function isUniversityRole(role?: string | null) { return ['faculty','professor','admin','super_admin'].includes(role || ''); }
export function isStudentRole(_role?: string | null) { return true; }
export function getPortalRedirect(_role?: string | null) { return '/dashboard'; }
export default function RoleGuard({children, allowedPortal}: {children: React.ReactNode; allowedPortal: 'student' | 'university'}) {
  const {status, user} = useAuthContext();
  const router = useRouter();
  const allowed = allowedPortal === 'student' || isUniversityRole(user?.institution_role);
  useEffect(() => { if (status === 'authenticated' && !allowed) router.replace('/dashboard'); }, [status, allowed, router]);
  return status === 'authenticated' && allowed ? <>{children}</> : null;
}
