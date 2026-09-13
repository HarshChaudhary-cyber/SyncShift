'use client';

import React, { useEffect, useState } from 'react';

export default function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    // Initial check (client-side only to prevent hydration mismatch)
    if (typeof window !== 'undefined' && !navigator.onLine) {
      setIsOffline(true);
    }

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="w-full bg-amber-500/15 border-b border-amber-500/30 text-amber-700 dark:text-amber-200 px-4 py-2 text-xs flex items-center justify-center gap-2 backdrop-blur-sm transition-all"
    >
      <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse shrink-0" />
      <span className="font-semibold">You're offline.</span>
      <span className="opacity-90">Previously loaded schedule is still available.</span>
    </div>
  );
}
