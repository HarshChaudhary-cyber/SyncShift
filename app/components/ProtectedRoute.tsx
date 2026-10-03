'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { status, error, refreshUser, logout } = useAuthContext();
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login?returnTo=' + encodeURIComponent(window.location.pathname + window.location.search));
    }
  }, [status, router]);

  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg
            width={32}
            height={32}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="animate-spin text-indigo-400"
            aria-hidden="true"
          >
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <p className="text-[var(--text-secondary)] text-sm">Verifying your session…</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--bg-primary)] text-[var(--text-primary)]"><div role="alert" className="max-w-md space-y-5"><h1 className="text-xl font-semibold">Session verification unavailable</h1><p>{error}</p><div className="flex gap-5"><button className="underline" onClick={refreshUser}>Retry verification</button><button className="underline" onClick={logout}>Return to sign in</button></div></div></div>;
  }
  if (status === 'unauthenticated') {
    return null;
  }

  return <>{children}</>;
}
