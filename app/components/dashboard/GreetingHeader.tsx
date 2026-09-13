'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import { DashboardUser } from '@/lib/api';

interface GreetingHeaderProps {
  user: DashboardUser | null;
  currentDate?: string; // YYYY-MM-DD
}

export default function GreetingHeader({ user, currentDate }: GreetingHeaderProps) {
  const router = useRouter();
  const { logout } = useAuthContext();

  // Determine greeting and date in useEffect to prevent server/client hydration mismatches
  const [timeGreeting, setTimeGreeting] = useState('Welcome');
  const [formattedDate, setFormattedDate] = useState('');

  useEffect(() => {
    const hour = new Date().getHours();
    let g = 'Good morning';
    if (hour >= 12 && hour < 17) {
      g = 'Good afternoon';
    } else if (hour >= 17) {
      g = 'Good evening';
    }
    setTimeGreeting(g);

    try {
      const d = currentDate ? new Date(currentDate + 'T00:00:00') : new Date();
      setFormattedDate(
        d.toLocaleDateString('en-GB', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })
      );
    } catch {
      setFormattedDate('Today');
    }
  }, [currentDate]);

  const displayName = user?.display_name || user?.email?.split('@')[0] || 'Student';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-4 sm:p-6 shadow-xl backdrop-blur-md mb-6 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left greeting and date */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1
              className="text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight text-[var(--text-primary)]"
              suppressHydrationWarning
            >
              {timeGreeting}, <span className="text-indigo-500 dark:text-indigo-400">{displayName}</span> 👋
            </h1>
          </div>
          <p className="text-xs text-indigo-400 font-medium">
            Plan classes, work, and life in one schedule.
          </p>
          <p className="text-xs sm:text-sm text-[var(--text-secondary)] flex items-center gap-2 font-medium">
            <span suppressHydrationWarning>📅 {formattedDate || 'Today'}</span>
            {user?.timezone && (
              <span className="hidden sm:inline text-[var(--text-muted)] font-mono text-xs">
                ({user.timezone})
              </span>
            )}
          </p>
        </div>

        {/* Right user pill, avatar & quick sign-out */}
        <div className="flex items-center gap-3 self-end sm:self-auto">
          <div className="flex items-center gap-2.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-full px-3 py-1.5 shadow-sm">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={displayName}
                className="w-7 h-7 rounded-full object-cover border border-[var(--border-color)]"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-inner">
                {initials || 'U'}
              </div>
            )}
            <span className="text-xs font-medium text-[var(--text-primary)] hidden md:inline max-w-[140px] truncate">
              {user?.email}
            </span>
          </div>

          <button
            onClick={() => {
              logout();
              router.push('/login');
            }}
            title="Sign out"
            className="px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-rose-500/10 text-[var(--text-secondary)] hover:text-rose-600 dark:hover:text-rose-400 border border-[var(--border-color)] hover:border-rose-500/30 rounded-lg text-xs font-medium transition cursor-pointer"
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
