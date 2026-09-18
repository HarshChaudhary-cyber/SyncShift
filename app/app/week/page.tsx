'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function WeekPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/student/calendar');
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center text-[var(--text-secondary)]">
        Loading schedule…
      </div>
    </ProtectedRoute>
  );
}
