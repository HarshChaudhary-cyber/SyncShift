'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import { useThemeContext } from '@/context/ThemeContext';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';

export interface SidebarNavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  /** If true, this item is only shown to admin/super_admin */
  adminOnly?: boolean;
}

interface PortalSidebarProps {
  /** The portal brand label, e.g. "Student Portal" or "University Portal" */
  portalLabel: string;
  /** Accent color class for the portal — controls the active item highlight */
  accentColor: 'indigo' | 'emerald';
  /** Navigation items to render */
  navItems: SidebarNavItem[];
  /** User's institutional role for filtering admin-only items */
  userRole?: string | null;
  /** Optional institution name to display */
  institutionName?: string | null;
  children: React.ReactNode;
}

// ── SVG Icon Components ────────────────────────────────────────────────────

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

export default function PortalSidebar({
  portalLabel,
  accentColor,
  navItems,
  userRole,
  institutionName,
  children,
}: PortalSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthContext();
  const { resolvedTheme, toggleTheme } = useThemeContext();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Close mobile sidebar when clicking outside
  useEffect(() => {
    if (!mobileOpen) return;
    const handler = (e: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
        setMobileOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [mobileOpen]);

  const isAdmin = userRole === 'admin' || userRole === 'super_admin';
  const filteredNavItems = navItems.filter((item) => !item.adminOnly || isAdmin);

  const accentClasses = {
    indigo: {
      activeBg: 'bg-indigo-500/15',
      activeText: 'text-indigo-600 dark:text-indigo-400',
      activeBorder: 'border-indigo-500',
      hoverBg: 'hover:bg-indigo-500/8',
      brandGradient: 'from-indigo-500 to-blue-600',
      brandBg: 'bg-indigo-500/10',
      brandBorder: 'border-indigo-500/30',
      brandText: 'text-indigo-600 dark:text-indigo-400',
    },
    emerald: {
      activeBg: 'bg-emerald-500/15',
      activeText: 'text-emerald-600 dark:text-emerald-400',
      activeBorder: 'border-emerald-500',
      hoverBg: 'hover:bg-emerald-500/8',
      brandGradient: 'from-emerald-500 to-teal-600',
      brandBg: 'bg-emerald-500/10',
      brandBorder: 'border-emerald-500/30',
      brandText: 'text-emerald-600 dark:text-emerald-400',
    },
  }[accentColor];

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const displayName = user?.display_name || user?.email?.split('@')[0] || 'User';
  const initials = displayName.slice(0, 2).toUpperCase();

  function renderSidebarContent() {
    return (
      <div className="flex flex-col h-full">
        {/* Brand / Portal Header */}
        <div className="px-4 pt-5 pb-4">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${accentClasses.brandGradient} flex items-center justify-center shadow-lg`}>
              <span className="text-white text-sm font-bold">⚡</span>
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <h1 className="text-sm font-bold text-[var(--text-primary)] tracking-tight truncate">
                  SyncShift
                </h1>
                <p className={`text-[10px] font-semibold ${accentClasses.brandText} tracking-wide uppercase`}>
                  {portalLabel}
                </p>
              </div>
            )}
          </div>
          {!collapsed && institutionName && (
            <div className={`mt-3 px-2.5 py-1.5 rounded-lg text-[10px] font-medium ${accentClasses.brandBg} ${accentClasses.brandText} border ${accentClasses.brandBorder} truncate`}>
              🏛️ {institutionName}
            </div>
          )}
        </div>

        {/* Collapse button (desktop only) */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden lg:flex items-center justify-center mx-3 mb-2 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronIcon open={collapsed} />
        </button>

        <div className="h-px bg-[var(--border-color)] mx-3 mb-2" />

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-2.5 space-y-0.5 pb-4">
          {filteredNavItems.map((item) => {
            const isActive =
              item.href === pathname ||
              (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-150 ${
                  isActive
                    ? `${accentClasses.activeBg} ${accentClasses.activeText} shadow-sm`
                    : `text-[var(--text-secondary)] ${accentClasses.hoverBg} hover:text-[var(--text-primary)]`
                } ${collapsed ? 'justify-center' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <span className={`text-base shrink-0 ${isActive ? '' : 'opacity-70 group-hover:opacity-100'}`}>
                  {item.icon}
                </span>
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Section */}
        <div className="mt-auto border-t border-[var(--border-color)] px-3 py-3 space-y-2">
          {/* Ask SyncShift */}
          {!collapsed && (
            <button
              onClick={() => openSyncShiftAssistant()}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 border border-indigo-500/25 text-indigo-700 dark:text-indigo-300 hover:text-indigo-950 dark:hover:text-white hover:border-indigo-400 transition cursor-pointer"
            >
              <span>✨</span>
              <span>Ask SyncShift</span>
            </button>
          )}

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer ${collapsed ? 'justify-center w-full' : 'w-full'}`}
            title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {resolvedTheme === 'dark' ? <SunIcon /> : <MoonIcon />}
            {!collapsed && <span>{resolvedTheme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>

          {/* User profile / Logout */}
          <div className={`flex items-center gap-2.5 px-2 py-2 rounded-xl ${collapsed ? 'justify-center' : ''}`}>
            <div className={`w-8 h-8 shrink-0 rounded-full bg-gradient-to-br ${accentClasses.brandGradient} flex items-center justify-center text-white text-xs font-bold shadow`}>
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full object-cover" />
              ) : (
                initials
              )}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-[var(--text-primary)] truncate">{displayName}</p>
                <p className="text-[10px] text-[var(--text-muted)] truncate">{user?.email}</p>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer"
                title="Sign out"
              >
                <LogoutIcon />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`
          fixed lg:sticky top-0 left-0 z-50 h-screen
          bg-[var(--bg-card)] border-r border-[var(--border-color)]
          transition-all duration-200 ease-out
          ${collapsed ? 'w-[68px]' : 'w-[260px]'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          flex flex-col
        `}
      >
        {/* Mobile close button */}
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 right-3 p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] lg:hidden cursor-pointer"
        >
          <CloseIcon />
        </button>

        {renderSidebarContent()}
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Top bar (mobile) */}
        <header className="sticky top-0 z-30 lg:hidden bg-[var(--bg-card)] border-b border-[var(--border-color)] px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
          >
            <MenuIcon />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-lg">⚡</span>
            <span className="text-sm font-bold text-[var(--text-primary)]">SyncShift</span>
            <span className={`text-[10px] font-semibold ${accentClasses.brandText} uppercase`}>
              {portalLabel}
            </span>
          </div>
          <div className="w-8" /> {/* Spacer for symmetry */}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
