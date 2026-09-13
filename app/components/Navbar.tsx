'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import { useThemeContext } from '@/context/ThemeContext';
import { api, NotificationLogItem } from '@/lib/api';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';

import OfflineBanner from '@/components/ui/OfflineBanner';

interface NavbarProps {
  onImportClick?: () => void;
}

export default function Navbar({ onImportClick }: NavbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthContext();
  const { resolvedTheme, toggleTheme } = useThemeContext();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationLogItem[]>([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const moreRef = useRef<HTMLDivElement>(null);

  const primaryNavLinks = [
    {
      name: 'Home',
      href: '/dashboard',
      icon: '🏠',
      isActive: pathname === '/dashboard',
    },
    {
      name: 'My Schedule',
      href: '/calendar',
      icon: '📅',
      isActive: pathname.startsWith('/calendar'),
    },
    {
      name: 'My Courses',
      href: '/student/academics',
      icon: '🎓',
      isActive: pathname.startsWith('/student'),
    },
    {
      name: 'Plan',
      href: '/planner',
      icon: '📖',
      isActive: pathname.startsWith('/planner'),
    },
  ];

  const secondaryNavLinks = [
    { name: 'Analytics', href: '/analytics', icon: '📊' },
    { name: 'University Portal', href: '/university', icon: '🏛️' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ];

  const handleImport = () => {
    if (onImportClick) {
      onImportClick();
    } else {
      router.push('/calendar?import=true');
    }
  };

  // Fetch today's notifications
  useEffect(() => {
    if (!user) return;
    async function loadNotifications() {
      try {
        setLoadingNotifications(true);
        const data = await api.getNotificationLog(true);
        setNotifications(data || []);
      } catch {
        // Fallback silently if unauthenticated or error
      } finally {
        setLoadingNotifications(false);
      }
    }
    loadNotifications();

    // Poll every 30 seconds for new alerts
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, [user]);

  // Click outside listener for dropdowns
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setMoreMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayName = user?.display_name || user?.email?.split('@')[0] || 'User';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const notifCount = notifications.length;

  return (
    <header className="border-b border-[var(--border-color)] bg-[var(--navbar-bg)] sticky top-0 z-40 backdrop-blur-md transition-colors duration-200">
      <OfflineBanner />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        {/* Brand & Desktop Navigation */}
        <div className="flex items-center gap-6 sm:gap-8">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-[var(--text-primary)] font-black text-lg tracking-tight hover:opacity-90 transition"
          >
            <span className="text-xl text-indigo-500">⚡</span>
            <span>SyncShift</span>
          </Link>

          {/* Desktop Links */}
          <nav className="hidden sm:flex items-center gap-1">
            {primaryNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  link.isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/30'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                }`}
              >
                <span>{link.icon}</span>
                <span>{link.name}</span>
              </Link>
            ))}

            {/* Ask SyncShift Trigger */}
            <button
              type="button"
              onClick={() => openSyncShiftAssistant()}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600/30 border border-indigo-500/30 transition-all flex items-center gap-1.5 cursor-pointer shrink-0"
              title="Open SyncShift Assistant"
            >
              <span>✨</span>
              <span>Ask SyncShift</span>
            </button>

            {/* More ▾ Dropdown */}
            <div className="relative" ref={moreRef}>
              <button
                type="button"
                onClick={() => setMoreMenuOpen(!moreMenuOpen)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1 cursor-pointer ${
                  pathname.startsWith('/analytics') ||
                  pathname.startsWith('/university') ||
                  pathname.startsWith('/settings')
                    ? 'bg-[var(--bg-secondary)] text-indigo-400 font-bold border border-indigo-500/30'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                }`}
              >
                <span>More</span>
                <span className="text-[10px] text-[var(--text-muted)]">▾</span>
              </button>

              {moreMenuOpen && (
                <div className="absolute left-0 mt-2 w-52 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl py-1.5 z-50 animate-fade-in text-[var(--text-primary)]">
                  {secondaryNavLinks.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMoreMenuOpen(false)}
                      className="w-full px-3.5 py-2 text-left text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition flex items-center gap-2"
                    >
                      <span>{item.icon}</span>
                      <span>{item.name}</span>
                    </Link>
                  ))}

                  <div className="pt-1 mt-1 border-t border-[var(--border-color)]">
                    <button
                      onClick={() => {
                        setMoreMenuOpen(false);
                        handleImport();
                      }}
                      className="w-full px-3.5 py-2 text-left text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition flex items-center gap-2 cursor-pointer"
                    >
                      <span>📁</span>
                      <span>Import Schedule</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </nav>
        </div>

        {/* User profile & Actions (Desktop) */}
        <div className="hidden sm:flex items-center gap-3">
          {/* Theme Quick Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] transition cursor-pointer shadow-xs"
            aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={resolvedTheme === 'dark' ? 'Switch to light mode (☀️)' : 'Switch to dark mode (🌙)'}
          >
            <span className="text-sm select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
          </button>

          {/* Notification Bell with Badge & Dropdown */}
          {user && (
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                className="relative p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] transition cursor-pointer shadow-xs"
                aria-label="Today's Notifications"
                title="Notifications"
              >
                <span className="text-sm">🔔</span>
                {notifCount > 0 && (
                  <span className="absolute -top-1 -right-1 px-1.5 py-0.5 min-w-4 rounded-full bg-indigo-600 text-[10px] font-black text-white leading-none shadow-sm flex items-center justify-center">
                    {notifCount > 9 ? '9+' : notifCount}
                  </span>
                )}
              </button>

              {/* Notifications Dropdown Panel */}
              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl overflow-hidden z-50 animate-fade-in text-[var(--text-primary)]">
                  <div className="p-3.5 border-b border-[var(--border-color)] flex items-center justify-between bg-[var(--bg-secondary)]">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[var(--text-primary)]">Today's Notifications</span>
                      {notifCount > 0 && (
                        <span className="px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-500 text-[10px] font-bold">
                          {notifCount}
                        </span>
                      )}
                    </div>
                    <Link
                      href="/settings?tab=notifications"
                      onClick={() => setNotificationsOpen(false)}
                      className="text-[11px] font-medium text-[var(--text-secondary)] hover:text-indigo-500 transition"
                    >
                      Settings ⚙️
                    </Link>
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-[var(--border-color)] custom-theme-scrollbar">
                    {loadingNotifications ? (
                      <div className="p-6 text-center text-xs text-[var(--text-muted)]">Loading alerts...</div>
                    ) : notifications.length === 0 ? (
                      <div className="p-6 text-center text-xs text-[var(--text-muted)]">
                        <span className="block text-xl mb-1.5">✓</span>
                        You're all caught up.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div key={n.id} className="p-3 hover:bg-[var(--bg-secondary)] transition">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs">
                                {n.channel === 'push' ? '🔔' : '📧'}
                              </span>
                              <span className="text-xs font-bold text-[var(--text-primary)]">
                                {n.title}
                              </span>
                            </div>
                            <span className="text-[10px] text-[var(--text-muted)]" suppressHydrationWarning>
                              {n.sent_at ? new Date(n.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                            </span>
                          </div>
                          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{n.body}</p>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="p-2.5 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] text-center">
                    <Link
                      href="/settings?tab=notifications"
                      onClick={() => setNotificationsOpen(false)}
                      className="text-xs text-indigo-500 hover:text-indigo-600 font-semibold transition"
                    >
                      Manage Notification Settings →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* User Profile Avatar with Menu */}
          {user && (
            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] text-xs transition cursor-pointer shadow-xs"
              >
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={displayName}
                    className="w-5 h-5 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-indigo-600 text-[10px] font-bold text-white flex items-center justify-center">
                    {initials}
                  </div>
                )}
                <span className="font-medium max-w-[140px] truncate">{displayName}</span>
                <span className="text-[10px] text-[var(--text-muted)]">▾</span>
              </button>

              {/* Avatar Menu Dropdown */}
              {profileMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl py-1.5 z-50 animate-fade-in divide-y divide-[var(--border-color)] text-[var(--text-primary)]">
                  <div className="px-4 py-2.5">
                    <p className="text-xs font-bold text-[var(--text-primary)] truncate">{displayName}</p>
                    <p className="text-[11px] text-[var(--text-muted)] truncate">{user.email}</p>
                  </div>

                  <div className="py-1">
                    <Link
                      href="/settings"
                      onClick={() => setProfileMenuOpen(false)}
                      className="w-full px-4 py-2 text-left text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition flex items-center gap-2"
                    >
                      <span>⚙️</span>
                      <span>Settings</span>
                    </Link>
                  </div>

                  <div className="py-1">
                    <button
                      onClick={() => {
                        setProfileMenuOpen(false);
                        logout();
                        router.push('/login');
                      }}
                      className="w-full px-4 py-2 text-left text-xs font-semibold text-red-500 hover:bg-red-500/10 transition flex items-center gap-2 cursor-pointer"
                    >
                      <span>🚪</span>
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {!user && (
            <Link
              href="/login"
              className="px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition"
            >
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile Actions: Theme Toggle, Bell & Hamburger */}
        <div className="sm:hidden flex items-center gap-2">
          {/* Mobile Theme Quick Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
            aria-label="Toggle light/dark theme"
            title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <span className="text-sm select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
          </button>

          {user && (
            <Link
              href="/settings"
              className="relative p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              aria-label="Settings & Notifications"
            >
              <span className="text-sm">🔔</span>
              {notifCount > 0 && (
                <span className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full bg-indigo-600 text-[9px] font-bold text-white leading-none">
                  {notifCount}
                </span>
              )}
            </Link>
          )}

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-[var(--border-color)] bg-[var(--bg-card)] px-4 py-3 space-y-3">
          {/* Primary Navigation */}
          <div className="space-y-1">
            {primaryNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm font-semibold transition ${
                  link.isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {link.icon} {link.name}
              </Link>
            ))}

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                openSyncShiftAssistant();
              }}
              className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 transition flex items-center gap-2 cursor-pointer"
            >
              <span>✨</span>
              <span>Ask SyncShift</span>
            </button>
          </div>

          {/* Secondary Tools */}
          <div className="pt-2 border-t border-[var(--border-color)] space-y-1">
            <p className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
              More Tools
            </p>
            {secondaryNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] transition"
              >
                {link.icon} {link.name}
              </Link>
            ))}

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                handleImport();
              }}
              className="w-full text-left px-3 py-2 rounded-lg text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] transition flex items-center gap-2 cursor-pointer"
            >
              <span>📁</span>
              <span>Import Schedule</span>
            </button>
          </div>

          {user && (
            <div className="pt-2 border-t border-[var(--border-color)] flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)] truncate max-w-[200px]">
                {user.email}
              </span>
              <button
                onClick={() => {
                  logout();
                  router.push('/login');
                }}
                className="text-xs text-red-500 hover:underline cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
