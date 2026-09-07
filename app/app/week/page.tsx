'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function WeekPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/calendar');
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-neutral-400">
        Loading schedule…
      </div>
    </ProtectedRoute>
  );
}
