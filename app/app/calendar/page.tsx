'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function CalendarRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/student/calendar');
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs">Opening Student Calendar…</p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
