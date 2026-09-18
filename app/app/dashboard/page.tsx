'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import { getPortalRedirect } from '@/components/RoleGuard';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function DashboardRedirectPage() {
  const router = useRouter();
  const { status, user } = useAuthContext();

  useEffect(() => {
    if (status === 'authenticated' && user) {
      router.replace(getPortalRedirect(user.institution_role));
    }
  }, [status, user, router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs">Opening your portal dashboard…</p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
