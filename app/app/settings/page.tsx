'use client';

import React, { Suspense, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import ProtectedRoute from '@/components/ProtectedRoute';
import TimePicker from '@/components/ui/TimePicker';
import { useAuthContext } from '@/context/AuthContext';
import {
  api,
  ApiError,
  NotificationLogItem,
  NotificationPrefs,
} from '@/lib/api';
import { getBrowserAndOs } from '@/lib/notificationHelpers';

import CustomSelect from '@/components/ui/CustomSelect';
import { TIMEZONE_OPTIONS } from '@/lib/timezones';
import { useThemeContext } from '@/context/ThemeContext';

type SettingsTab = 'profile' | 'notifications' | 'preferences' | 'security' | 'danger';

const REMINDER_OPTIONS = [
  { value: 0, label: '0 minutes (At start)' },
  { value: 15, label: '15 minutes before' },
  { value: 30, label: '30 minutes before' },
  { value: 60, label: '60 minutes (1 hour) before' },
  { value: 120, label: '120 minutes (2 hours) before' },
];

const TRANSITION_BUFFER_OPTIONS = [
  { value: 0, label: '0 minutes (No buffer)' },
  { value: 10, label: '10 minutes' },
  { value: 15, label: '15 minutes (Standard buffer)' },
  { value: 30, label: '30 minutes (Moderate travel)' },
  { value: 45, label: '45 minutes' },
  { value: 60, label: '60 minutes (1 hour travel)' },
];

const CURRENCY_OPTIONS = [
  { value: 'INR', label: '₹ INR (Indian Rupee)' },
  { value: 'USD', label: '$ USD (US Dollar)' },
  { value: 'EUR', label: '€ EUR (Euro)' },
  { value: 'GBP', label: '£ GBP (British Pound)' },
  { value: 'JPY', label: '¥ JPY (Japanese Yen)' },
  { value: 'CAD', label: '$ CAD (Canadian Dollar)' },
  { value: 'AUD', label: '$ AUD (Australian Dollar)' },
  { value: 'CHF', label: 'CHF (Swiss Franc)' },
];

const LANGUAGE_OPTIONS = [
  { value: 'en', label: '🇬🇧 English' },
  { value: 'de', label: '🇩🇪 Deutsch (German)' },
  { value: 'hi', label: '🇮🇳 Hindi' },
  { value: 'fr', label: '🇫🇷 Français (French)' },
  { value: 'es', label: '🇪🇸 Español (Spanish)' },
];

// Curated comprehensive list of student timezones
const POPULAR_TIMEZONES = [
  'Europe/London',
  'Asia/Kolkata',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Toronto',
  'America/Vancouver',
  'Europe/Dublin',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Amsterdam',
  'Australia/Sydney',
  'Australia/Melbourne',
  'Asia/Dubai',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Asia/Hong_Kong',
  'Pacific/Auckland',
];

function getTimezoneOffsetString(tz: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      timeZoneName: 'shortOffset',
    });
    const parts = formatter.formatToParts(new Date());
    const tzPart = parts.find((p) => p.type === 'timeZoneName');
    return tzPart ? tzPart.value : '';
  } catch {
    return '';
  }
}

export function SettingsContent({ showNavbar = true }: { showNavbar?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, refreshUser, logout } = useAuthContext();

  // Active tab state
  const tabParam = searchParams.get('tab') as SettingsTab | null;
  const [activeTab, setActiveTab] = useState<SettingsTab>(
    tabParam && ['profile', 'notifications', 'preferences', 'security', 'danger'].includes(tabParam)
      ? tabParam
      : 'profile'
  );

  useEffect(() => {
    if (tabParam && ['profile', 'notifications', 'preferences', 'security', 'danger'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  // Toast Notification state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error'; id: number } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    const id = Date.now();
    setToast({ message, type, id });
    setTimeout(() => {
      setToast((current) => (current?.id === id ? null : current));
    }, 3000);
  };

  // ---------------------------------------------------------------------------
  // PROFILE STATE
  // ---------------------------------------------------------------------------
  const [displayName, setDisplayName] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [timezone, setTimezone] = useState('Europe/London');
  const [weeklyLimit, setWeeklyLimit] = useState<number>(20);
  const [savingProfile, setSavingProfile] = useState(false);
  const [tzSearch, setTzSearch] = useState('');
  const [tzDropdownOpen, setTzDropdownOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // PREFERENCES STATE
  // ---------------------------------------------------------------------------
  const [currency, setCurrency] = useState('INR');
  const [language, setLanguage] = useState('en');
  const { theme, changeTheme } = useThemeContext();
  const [weekStartsOn, setWeekStartsOn] = useState<'monday' | 'sunday'>('monday');
  const [timeFormat, setTimeFormat] = useState<'12h' | '24h'>('12h');
  const [minimumTransitionMinutes, setMinimumTransitionMinutes] = useState<number>(15);
  const [savingPrefs, setSavingPrefs] = useState(false);

  // ---------------------------------------------------------------------------
  // NOTIFICATIONS STATE
  // ---------------------------------------------------------------------------
  const [notifLoading, setNotifLoading] = useState(false);
  const [savingNotifs, setSavingNotifs] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [classReminderMin, setClassReminderMin] = useState(30);
  const [shiftReminderMin, setShiftReminderMin] = useState(60);
  const [studyReminderMin, setStudyReminderMin] = useState(15);
  const [deadlineReminder, setDeadlineReminder] = useState(true);
  const [conflictAlerts, setConflictAlerts] = useState(true);
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState('08:00');
  const [testSending, setTestSending] = useState(false);
  const [recentLogs, setRecentLogs] = useState<NotificationLogItem[]>([]);

  // ---------------------------------------------------------------------------
  // SECURITY & AUDIT STATE
  // ---------------------------------------------------------------------------
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [browserInfo, setBrowserInfo] = useState('Web Browser');
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAuditLogs, setLoadingAuditLogs] = useState(false);

  // ---------------------------------------------------------------------------
  // DANGER ZONE STATE
  // ---------------------------------------------------------------------------
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deletePassword, setDeletePassword] = useState('');
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [exportingData, setExportingData] = useState(false);

  // Initialize values from user profile
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || user.email.split('@')[0]);
      setAvatarUrl(user.avatar_url || '');
      setTimezone(user.timezone || 'Europe/London');
      setWeeklyLimit(user.weekly_work_hour_limit ?? 20);
      setCurrency(user.currency || 'INR');
      setLanguage(user.language || 'en');
      setMinimumTransitionMinutes(user.minimum_transition_minutes ?? 15);
      if (user.theme && !localStorage.getItem('syncshift-theme')) {
        changeTheme(user.theme as any);
      }
    }
    if (typeof window !== 'undefined') {
      setBrowserInfo(getBrowserAndOs());
      const savedWeekStart = localStorage.getItem('syncshift_week_starts_on') as 'monday' | 'sunday' | null;
      if (savedWeekStart) setWeekStartsOn(savedWeekStart);
      const savedTimeFormat = localStorage.getItem('syncshift_time_format') as '12h' | '24h' | null;
      if (savedTimeFormat) setTimeFormat(savedTimeFormat);
    }
  }, [user]);

  // Load audit logs when security tab is active
  useEffect(() => {
    if (activeTab === 'security' && user) {
      setLoadingAuditLogs(true);
      api.getAuditLogs(20, 0)
        .then((res) => setAuditLogs(res.items || []))
        .catch(() => {})
        .finally(() => setLoadingAuditLogs(false));
    }
  }, [activeTab, user]);

  // Load notification prefs & logs
  useEffect(() => {
    async function loadNotificationData() {
      if (!user) return;
      try {
        setNotifLoading(true);
        const [prefs, logs] = await Promise.all([
          api.getNotificationPrefs(),
          api.getNotificationLog(false).catch(() => []),
        ]);
        setPushEnabled(prefs.push_enabled);
        setEmailEnabled(prefs.email_enabled);
        setClassReminderMin(prefs.class_reminder_min);
        setShiftReminderMin(prefs.shift_reminder_min);
        setStudyReminderMin(prefs.study_reminder_min);
        setDeadlineReminder(prefs.deadline_reminder);
        setConflictAlerts(prefs.conflict_alerts);
        if (prefs.quiet_hours_start && prefs.quiet_hours_end) {
          setQuietHoursEnabled(true);
          setQuietHoursStart(prefs.quiet_hours_start);
          setQuietHoursEnd(prefs.quiet_hours_end);
        } else {
          setQuietHoursEnabled(false);
        }
        setRecentLogs(logs.slice(0, 5));
      } catch (err: any) {
        console.error('Failed to load notification settings:', err);
      } finally {
        setNotifLoading(false);
      }
    }
    loadNotificationData();
  }, [user]);

  // Available Timezones list (deduped)
  const allTimezones = useMemo(() => {
    let list = [...POPULAR_TIMEZONES];
    if (typeof Intl !== 'undefined' && typeof (Intl as any).supportedValuesOf === 'function') {
      try {
        const supported = (Intl as any).supportedValuesOf('timeZone');
        list = Array.from(new Set([...list, ...supported]));
      } catch {
        // fallback to curated list
      }
    }
    return list;
  }, []);

  const filteredTimezones = useMemo(() => {
    if (!tzSearch.trim()) return allTimezones.slice(0, 40);
    const q = tzSearch.toLowerCase();
    return allTimezones.filter((tz) => tz.toLowerCase().includes(q)).slice(0, 40);
  }, [allTimezones, tzSearch]);

  // Password complexity checks
  const passwordHasLength = newPassword.length >= 8;
  const passwordHasUpper = /[A-Z]/.test(newPassword);
  const passwordHasNumber = /\d/.test(newPassword);
  const isPasswordValid = passwordHasLength && passwordHasUpper && passwordHasNumber;
  const doPasswordsMatch = newPassword === confirmPassword;

  // Account provider label
  const oauthProviderName = useMemo(() => {
    if (user?.oauth_provider === 'google') return 'Google';
    if (user?.oauth_provider === 'microsoft') return 'Microsoft';
    if (user?.oauth_provider === 'facebook') return 'Facebook';
    if (user?.oauth_provider === 'apple') return 'Apple';
    return user?.has_password ? 'Email & Password' : 'Email Account';
  }, [user]);

  // Initials for avatar fallback
  const initials = useMemo(() => {
    const name = displayName || user?.email || 'U';
    return name
      .split(' ')
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }, [displayName, user]);

  // ---------------------------------------------------------------------------
  // HANDLERS
  // ---------------------------------------------------------------------------

  const handleSaveProfile = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSavingProfile(true);
      await api.updateProfile({
        display_name: displayName.trim(),
        timezone,
        weekly_work_hour_limit: Number(weeklyLimit),
        avatar_url: avatarUrl.trim() || null,
      });
      await refreshUser();
      showToast('Profile updated successfully ✓', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to update profile', 'error');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSavePreferences = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSavingPrefs(true);
      if (typeof window !== 'undefined') {
        localStorage.setItem('syncshift_week_starts_on', weekStartsOn);
        localStorage.setItem('syncshift_time_format', timeFormat);
      }
      await api.updateProfile({
        currency,
        language,
        theme,
        minimum_transition_minutes: Number(minimumTransitionMinutes),
      });
      await refreshUser();
      showToast('Preferences saved successfully ✓', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save preferences', 'error');
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleSaveNotifications = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSavingNotifs(true);
      await api.updateNotificationPrefs({
        push_enabled: pushEnabled,
        email_enabled: emailEnabled,
        class_reminder_min: classReminderMin,
        shift_reminder_min: shiftReminderMin,
        study_reminder_min: studyReminderMin,
        deadline_reminder: deadlineReminder,
        conflict_alerts: conflictAlerts,
        quiet_hours_start: quietHoursEnabled ? quietHoursStart : null,
        quiet_hours_end: quietHoursEnabled ? quietHoursEnd : null,
      });
      showToast('Notification settings saved ✓', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save notification settings', 'error');
    } finally {
      setSavingNotifs(false);
    }
  };

  const handleSendTestNotification = async () => {
    try {
      setTestSending(true);
      const res = await api.sendTestNotification();
      showToast(res.message || 'Test notification sent 🎉', 'success');
      // Refresh logs
      const updatedLogs = await api.getNotificationLog(false);
      setRecentLogs(updatedLogs.slice(0, 5));
    } catch (err: any) {
      showToast(err.message || 'Could not send test notification. Allow browser push first.', 'error');
    } finally {
      setTestSending(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      showToast('Please enter your current password', 'error');
      return;
    }
    if (!isPasswordValid) {
      showToast('New password must be at least 8 characters with 1 uppercase letter and 1 number', 'error');
      return;
    }
    if (!doPasswordsMatch) {
      showToast('New password confirmation does not match', 'error');
      return;
    }
    try {
      setSavingPassword(true);
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Password changed successfully ✓', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to change password', 'error');
    } finally {
      setSavingPassword(false);
    }
  };

  const handleSignOutAllDevices = () => {
    logout();
    router.push('/login');
  };

  const handleExportData = async () => {
    try {
      setExportingData(true);
      const exportData = await api.exportData();
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `syncshift-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Data exported successfully! Check your downloads ✓', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to export schedule data', 'error');
    } finally {
      setExportingData(false);
    }
  };

  const handleDeleteAccount = async () => {
    const isEmailUser = user?.has_password || !user?.oauth_provider;
    if (isEmailUser && !deletePassword) {
      showToast('Please enter your account password to confirm deletion', 'error');
      return;
    }
    if (deleteConfirmText.trim() !== 'DELETE') {
      showToast('Please type DELETE in capital letters to confirm', 'error');
      return;
    }
    try {
      setDeletingAccount(true);
      await api.deleteAccount({
        password: deletePassword || undefined,
        confirm: deleteConfirmText.trim(),
      });
      setDeleteModalOpen(false);
      logout();
      router.push('/login');
    } catch (err: any) {
      showToast(err.message || 'Failed to delete account', 'error');
    } finally {
      setDeletingAccount(false);
    }
  };

  return (
    <div className={showNavbar ? "min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col transition-colors duration-200" : "text-[var(--text-primary)] transition-colors duration-200"}>
      {showNavbar && <Navbar />}

      {/* Floating Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border backdrop-blur-md transition-all animate-slide-in ${
            toast.type === 'success'
              ? 'bg-[var(--bg-card)] border-emerald-500/60 text-emerald-500'
              : 'bg-[var(--bg-card)] border-red-500/60 text-red-500'
          }`}
        >
          <span className="text-lg">{toast.type === 'success' ? '✓' : '⚠️'}</span>
          <span className="text-xs font-semibold text-[var(--text-primary)]">{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            className="ml-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-[var(--text-primary)] flex items-center gap-2.5">
            <span>⚙️</span>
            <span>Settings</span>
          </h1>
          <p className="text-xs sm:text-sm text-[var(--text-secondary)] mt-1">
            Manage your personal profile, notifications, display preferences, and account security.
          </p>
        </div>

        {/* Mobile Horizontal Tabs (Full width, scrollable, 360px safe) */}
        <div className="md:hidden flex items-center gap-1.5 overflow-x-auto pb-2 mb-6 border-b border-[var(--border-color)] scrollbar-none">
          {[
            { id: 'profile', label: 'Profile', icon: '👤' },
            { id: 'notifications', label: 'Notifications', icon: '🔔' },
            { id: 'preferences', label: 'Preferences', icon: '🎨' },
            { id: 'security', label: 'Security', icon: '🔒' },
            { id: 'danger', label: 'Danger Zone', icon: '⚠️' },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as SettingsTab)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                  isActive
                    ? tab.id === 'danger'
                      ? 'bg-red-600 text-white shadow-md shadow-red-950/40'
                      : 'bg-indigo-600 text-white shadow-md shadow-indigo-950/40'
                    : 'bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Desktop Layout: Sidebar + Main Panels */}
        <div className="flex flex-col md:flex-row gap-6 lg:gap-8 items-start">
          {/* Desktop Left Sidebar */}
          <aside className="hidden md:block w-64 shrink-0 sticky top-20 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-2.5 shadow-sm">
            <nav className="space-y-1">
              {[
                { id: 'profile', label: 'Profile', icon: '👤', desc: 'Personal info & timezone' },
                { id: 'notifications', label: 'Notifications', icon: '🔔', desc: 'Reminders & quiet hours' },
                { id: 'preferences', label: 'Preferences', icon: '🎨', desc: 'Currency & display options' },
                { id: 'security', label: 'Security', icon: '🔒', desc: 'Password & active sessions' },
                { id: 'danger', label: 'Danger Zone', icon: '⚠️', desc: 'Export & account deletion' },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                const isDanger = tab.id === 'danger';
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as SettingsTab)}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl text-left transition cursor-pointer ${
                      isActive
                        ? isDanger
                          ? 'bg-red-500/10 border border-red-500/50 text-red-500'
                          : 'bg-indigo-600/15 border border-indigo-500/50 text-[var(--text-primary)] font-bold'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] border border-transparent'
                    }`}
                  >
                    <span className="text-lg mt-0.5">{tab.icon}</span>
                    <div>
                      <div className={`text-xs font-bold ${isActive ? (isDanger ? 'text-red-500' : 'text-indigo-500') : 'text-[var(--text-primary)]'}`}>
                        {tab.label}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] leading-tight mt-0.5">{tab.desc}</div>
                    </div>
                  </button>
                );
              })}
            </nav>
          </aside>

          {/* Right Content Panels */}
          <div className="flex-1 w-full space-y-6 min-w-0">
            {/* ------------------------------------------------------------- */}
            {/* 1. PROFILE SECTION */}
            {/* ------------------------------------------------------------- */}
            {activeTab === 'profile' && (
              <section className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-7 shadow-xl space-y-6 animate-fade-in text-[var(--text-primary)]">
                <div className="border-b border-[var(--border-color)] pb-4">
                  <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <span>👤</span>
                    <span>Student Profile</span>
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    Update your display name, avatar, and study timezone.
                  </p>
                </div>

                <form onSubmit={handleSaveProfile} className="space-y-6">
                  {/* Avatar section */}
                  <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    <div className="relative w-16 h-16 rounded-full overflow-hidden border-2 border-indigo-500/40 bg-neutral-800 flex items-center justify-center shrink-0 shadow-inner">
                      {avatarUrl ? (
                        <img src={avatarUrl} alt="Avatar" className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-xl font-black text-indigo-400">{initials}</span>
                      )}
                    </div>
                    <div className="flex-1 space-y-1.5">
                      <label className="block text-xs font-semibold text-neutral-300">
                        Profile Avatar URL
                      </label>
                      <input
                        type="url"
                        value={avatarUrl}
                        onChange={(e) => setAvatarUrl(e.target.value)}
                        placeholder="https://example.com/avatar.jpg"
                        className="w-full px-3.5 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                      />
                      <p className="text-[11px] text-[var(--text-muted)]">
                        Direct image link or leave empty to display your initials circle.
                      </p>
                    </div>
                  </div>

                  {/* Display Name */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[var(--text-secondary)]">Display Name</label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      required
                      placeholder="e.g. Harsh Patel"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                    />
                  </div>

                  {/* Email & Account Badge */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-semibold text-[var(--text-secondary)]">Email Address</label>
                      <span className="px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[10px] font-bold text-[var(--text-secondary)] flex items-center gap-1">
                        <span>🛡️</span>
                        <span>{oauthProviderName}</span>
                      </span>
                    </div>
                    <input
                      type="email"
                      value={user?.email || ''}
                      disabled
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-muted)] cursor-not-allowed"
                    />
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Your registered email cannot be edited directly for security reasons.
                    </p>
                  </div>

                  {/* Timezone (Searchable CustomSelect) */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                      Timezone (IANA)
                    </label>
                    <CustomSelect
                      options={TIMEZONE_OPTIONS}
                      value={timezone}
                      onChange={(val) => setTimezone(String(val))}
                      searchable={true}
                      placeholder="Search timezone (e.g. London, Kolkata, New York)..."
                    />
                    <p className="text-[11px] text-[var(--text-muted)]">
                      All schedules, conflict detection, and notifications will be synchronized to this timezone.
                    </p>
                  </div>

                  {/* Weekly Work Hour Limit */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                      Weekly Work Hour Limit (Hours/Week)
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        min="0"
                        max="168"
                        step="0.5"
                        value={weeklyLimit}
                        onChange={(e) => setWeeklyLimit(parseFloat(e.target.value) || 0)}
                        required
                        className="w-36 px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition"
                      />
                      <span className="text-xs text-[var(--text-secondary)] font-medium">hours / week</span>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed">
                      💡 Set to match your student visa work allowance (e.g. 20h/week for UK Student Visa, 24h/week in Canada). Your dashboard will trigger automated alerts when shifts approach this threshold.
                    </p>
                  </div>

                  {/* Save Profile Button */}
                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={savingProfile}
                      className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-950/50 transition cursor-pointer flex items-center gap-2"
                    >
                      {savingProfile ? (
                        <>
                          <span className="animate-spin text-xs">⌛</span>
                          <span>Saving...</span>
                        </>
                      ) : (
                        <span>Save Profile Changes</span>
                      )}
                    </button>
                  </div>
                </form>
              </section>
            )}

            {/* ------------------------------------------------------------- */}
            {/* 2. NOTIFICATIONS SECTION */}
            {/* ------------------------------------------------------------- */}
            {activeTab === 'notifications' && (
              <section className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-7 shadow-xl space-y-6 animate-fade-in text-[var(--text-primary)]">
                <div className="border-b border-[var(--border-color)] pb-4 flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                      <span>🔔</span>
                      <span>Notification Preferences</span>
                    </h2>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                      Configure class reminders, work shift alerts, quiet hours, and push channels.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleSendTestNotification}
                    disabled={testSending}
                    className="px-3.5 py-1.5 rounded-xl bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-xs font-semibold text-neutral-200 transition flex items-center gap-2 cursor-pointer"
                  >
                    {testSending ? (
                      <>
                        <span className="animate-spin text-xs">⌛</span>
                        <span>Sending...</span>
                      </>
                    ) : (
                      <>
                        <span>📲</span>
                        <span>Send Test Alert</span>
                      </>
                    )}
                  </button>
                </div>

                <form onSubmit={handleSaveNotifications} className="space-y-6">
                  {/* Delivery Channels */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-neutral-300 uppercase tracking-wider">
                      Channels
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {/* Push Toggle */}
                      <label className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] cursor-pointer hover:border-[var(--border-hover)] transition">
                        <div>
                          <span className="text-xs font-bold text-[var(--text-primary)] block">Browser Push Alerts</span>
                          <span className="text-[11px] text-[var(--text-muted)] block">Instant desktop/mobile notification</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={pushEnabled}
                          onChange={(e) => setPushEnabled(e.target.checked)}
                          className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                        />
                      </label>

                      {/* Email Toggle */}
                      <label className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] cursor-pointer hover:border-[var(--border-hover)] transition">
                        <div>
                          <span className="text-xs font-bold text-[var(--text-primary)] block">Email Reminders</span>
                          <span className="text-[11px] text-[var(--text-muted)] block">Daily digest & critical notices</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={emailEnabled}
                          onChange={(e) => setEmailEnabled(e.target.checked)}
                          className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                        />
                      </label>
                    </div>
                  </div>

                  {/* Reminder Timing Dropdowns */}
                  <div className="space-y-3 pt-2">
                    <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                      Remind Me Before
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {/* Class */}
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                          🎓 Lectures & Classes
                        </label>
                        <CustomSelect
                          options={REMINDER_OPTIONS}
                          value={classReminderMin}
                          onChange={(v) => setClassReminderMin(Number(v))}
                          size="sm"
                        />
                      </div>

                      {/* Shift */}
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                          💼 Work Shifts
                        </label>
                        <CustomSelect
                          options={REMINDER_OPTIONS}
                          value={shiftReminderMin}
                          onChange={(v) => setShiftReminderMin(Number(v))}
                          size="sm"
                        />
                      </div>

                      {/* Study */}
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                          📖 Study Blocks
                        </label>
                        <CustomSelect
                          options={REMINDER_OPTIONS}
                          value={studyReminderMin}
                          onChange={(v) => setStudyReminderMin(Number(v))}
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Checkboxes: Deadlines & Conflicts */}
                  <div className="space-y-2.5 pt-2">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={deadlineReminder}
                        onChange={(e) => setDeadlineReminder(e.target.checked)}
                        className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                      />
                      <span className="text-xs text-[var(--text-primary)]">
                        Remind me 1 day before assignment & task deadlines
                      </span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={conflictAlerts}
                        onChange={(e) => setConflictAlerts(e.target.checked)}
                        className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                      />
                      <span className="text-xs text-[var(--text-primary)]">
                        Alert me immediately when a new shift or class conflict is detected
                      </span>
                    </label>
                  </div>

                  {/* Quiet Hours */}
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xs font-bold text-[var(--text-primary)] block">🌙 Quiet Hours (Do Not Disturb)</span>
                        <span className="text-[11px] text-[var(--text-muted)] block">
                          Mute notifications during designated sleep or study hours
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={quietHoursEnabled}
                        onChange={(e) => setQuietHoursEnabled(e.target.checked)}
                        className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                      />
                    </div>

                    {quietHoursEnabled && (
                      <div className="pt-2 flex items-center gap-3 flex-wrap">
                        <div>
                          <label className="block text-[11px] text-[var(--text-secondary)] mb-1">From</label>
                          <TimePicker value={quietHoursStart} onChange={setQuietHoursStart} />
                        </div>
                        <span className="text-[var(--text-muted)] text-xs mt-4">to</span>
                        <div>
                          <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Until</label>
                          <TimePicker value={quietHoursEnd} onChange={setQuietHoursEnd} />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Save Notifications Button */}
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={savingNotifs}
                      className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-950/50 transition cursor-pointer flex items-center gap-2"
                    >
                      {savingNotifs ? 'Saving...' : 'Save Notification Preferences'}
                    </button>
                  </div>
                </form>

                {/* Recent Notifications Log */}
                <div className="pt-4 border-t border-[var(--border-color)]">
                  <h3 className="text-xs font-bold text-[var(--text-primary)] mb-3 flex items-center gap-2">
                    <span>📜</span>
                    <span>Recent Notification History</span>
                  </h3>
                  {recentLogs.length === 0 ? (
                    <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center text-xs text-[var(--text-muted)]">
                      No recent notifications sent yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {recentLogs.map((log) => (
                        <div
                          key={log.id}
                          className="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-start justify-between gap-3 text-xs"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-[var(--text-primary)]">{log.title}</span>
                              <span className="px-1.5 py-0.2 rounded text-[10px] uppercase font-bold bg-[var(--bg-input)] text-[var(--text-secondary)]">
                                {log.channel}
                              </span>
                            </div>
                            <p className="text-[var(--text-secondary)] text-[11px] mt-0.5">{log.body}</p>
                          </div>
                          <span className="text-[10px] text-[var(--text-muted)] shrink-0 font-mono" suppressHydrationWarning>
                            {new Date(log.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* ------------------------------------------------------------- */}
            {/* 3. PREFERENCES SECTION */}
            {/* ------------------------------------------------------------- */}
            {activeTab === 'preferences' && (
              <section className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-7 shadow-xl space-y-6 animate-fade-in text-[var(--text-primary)]">
                <div className="border-b border-[var(--border-color)] pb-4">
                  <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <span>🎨</span>
                    <span>App Preferences</span>
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    Customize your display currency, calendar conventions, and system theme.
                  </p>
                </div>

                <form onSubmit={handleSavePreferences} className="space-y-6">
                  {/* Currency */}
                  {/* Currency */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-neutral-300">
                      Display Currency
                    </label>
                    <div className="max-w-sm">
                      <CustomSelect
                        options={CURRENCY_OPTIONS}
                        value={currency}
                        onChange={(val) => setCurrency(String(val))}
                      />
                    </div>
                    <p className="text-[11px] text-neutral-500">
                      Updates the wage and expected earnings currency symbol across your dashboard and shift blocks.
                    </p>
                  </div>

                  {/* Language */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-neutral-300">
                      Language
                    </label>
                    <div className="max-w-sm">
                      <CustomSelect
                        options={LANGUAGE_OPTIONS}
                        value={language}
                        onChange={(val) => setLanguage(String(val))}
                      />
                    </div>
                    <p className="text-[11px] text-neutral-500">
                      Selected language preference (multi-language interface strings will be supported in upcoming releases).
                    </p>
                  </div>

                  {/* Theme */}
                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-[var(--text-primary)]">Theme</label>
                    <div className="grid grid-cols-3 gap-3 max-w-sm">
                      {[
                        { id: 'dark', label: 'Dark Mode', icon: '🌙' },
                        { id: 'light', label: 'Light Mode', icon: '☀️' },
                        { id: 'system', label: 'System', icon: '💻' },
                      ].map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => changeTheme(t.id as any)}
                          className={`p-3 rounded-xl border text-center transition cursor-pointer ${
                            theme === t.id
                              ? 'bg-indigo-600/15 border-indigo-500 text-[var(--text-primary)] font-bold ring-2 ring-indigo-500/20'
                              : 'bg-[var(--bg-input)] border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)]'
                          }`}
                        >
                          <span className="block text-lg mb-1">{t.icon}</span>
                          <span className="text-xs">{t.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Week Starts On */}
                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-neutral-300">
                      Week Starts On
                    </label>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setWeekStartsOn('monday')}
                        className={`px-4 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer ${
                          weekStartsOn === 'monday'
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        Monday (Academic Standard)
                      </button>
                      <button
                        type="button"
                        onClick={() => setWeekStartsOn('sunday')}
                        className={`px-4 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer ${
                          weekStartsOn === 'sunday'
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        Sunday
                      </button>
                    </div>
                  </div>

                  {/* Time Format */}
                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                      Time Format
                    </label>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setTimeFormat('12h')}
                        className={`px-4 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer ${
                          timeFormat === '12h'
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        12-Hour (e.g. 02:30 PM)
                      </button>
                      <button
                        type="button"
                        onClick={() => setTimeFormat('24h')}
                        className={`px-4 py-2 rounded-xl border text-xs font-semibold transition cursor-pointer ${
                          timeFormat === '24h'
                            ? 'bg-indigo-600 text-white border-indigo-500'
                            : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        24-Hour (e.g. 14:30)
                      </button>
                    </div>
                  </div>

                  {/* Minimum Transition Buffer */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                      Minimum Transition Buffer between Locations
                    </label>
                    <div className="max-w-sm">
                      <CustomSelect
                        options={TRANSITION_BUFFER_OPTIONS}
                        value={minimumTransitionMinutes}
                        onChange={(val) => setMinimumTransitionMinutes(Number(val))}
                      />
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Configured buffer between back-to-back classes and work shifts at different locations. Prevents unrealistic transitions and triggers warnings when commute time is insufficient. (Events at the exact same location bypass this buffer).
                    </p>
                  </div>

                  {/* Save Preferences Button */}
                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={savingPrefs}
                      className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-950/50 transition cursor-pointer flex items-center gap-2"
                    >
                      {savingPrefs ? 'Saving...' : 'Save Preferences'}
                    </button>
                  </div>
                </form>
              </section>
            )}

            {/* ------------------------------------------------------------- */}
            {/* 4. SECURITY SECTION */}
            {/* ------------------------------------------------------------- */}
            {activeTab === 'security' && (
              <section className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-7 shadow-xl space-y-6 animate-fade-in text-[var(--text-primary)]">
                <div className="border-b border-[var(--border-color)] pb-4">
                  <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <span>🔒</span>
                    <span>Account Security</span>
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    Manage your credentials, authentication methods, and active browser sessions.
                  </p>
                </div>

                {/* Authentication Method Badge */}
                <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Sign-in Method</span>
                    <span className="text-[11px] text-[var(--text-secondary)]">
                      {user?.oauth_provider
                        ? `Signed in via ${oauthProviderName} OAuth`
                        : 'Signed in with email and master password'}
                    </span>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-bold">
                    {oauthProviderName}
                  </span>
                </div>

                {/* For Email/Password Users: Change Password Form */}
                {user?.has_password ? (
                  <form onSubmit={handleChangePassword} className="space-y-4 pt-2">
                    <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                      Change Account Password
                    </h3>

                    {/* Current Password */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                        Current Password
                      </label>
                      <div className="relative">
                        <input
                          type={showCurrentPassword ? 'text' : 'password'}
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          required
                          placeholder="Enter your existing password"
                          className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          className="absolute right-3 top-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs cursor-pointer"
                        >
                          {showCurrentPassword ? '🙈' : '👁️'}
                        </button>
                      </div>
                    </div>

                    {/* New Password */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                        New Password
                      </label>
                      <div className="relative">
                        <input
                          type={showNewPassword ? 'text' : 'password'}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          required
                          placeholder="At least 8 chars, 1 uppercase, 1 number"
                          className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          className="absolute right-3 top-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs cursor-pointer"
                        >
                          {showNewPassword ? '🙈' : '👁️'}
                        </button>
                      </div>

                      {/* Password Strength Indicator */}
                      <div className="p-2.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1 text-[11px]">
                        <div className={`flex items-center gap-1.5 ${passwordHasLength ? 'text-emerald-500' : 'text-[var(--text-muted)]'}`}>
                          <span>{passwordHasLength ? '✓' : '○'}</span>
                          <span>At least 8 characters</span>
                        </div>
                        <div className={`flex items-center gap-1.5 ${passwordHasUpper ? 'text-emerald-500' : 'text-[var(--text-muted)]'}`}>
                          <span>{passwordHasUpper ? '✓' : '○'}</span>
                          <span>At least one uppercase letter (A-Z)</span>
                        </div>
                        <div className={`flex items-center gap-1.5 ${passwordHasNumber ? 'text-emerald-500' : 'text-[var(--text-muted)]'}`}>
                          <span>{passwordHasNumber ? '✓' : '○'}</span>
                          <span>At least one number (0-9)</span>
                        </div>
                      </div>
                    </div>

                    {/* Confirm Password */}
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        placeholder="Re-enter your new password"
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                      />
                      {confirmPassword && !doPasswordsMatch && (
                        <p className="text-[11px] text-red-500">Passwords do not match.</p>
                      )}
                    </div>

                    <div className="pt-2 flex justify-end">
                      <button
                        type="submit"
                        disabled={savingPassword || !isPasswordValid || !doPasswordsMatch}
                        className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-950/50 transition cursor-pointer"
                      >
                        {savingPassword ? 'Updating Password...' : 'Update Password'}
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1.5 text-xs text-[var(--text-secondary)]">
                    <p className="font-semibold text-[var(--text-primary)]">
                      Your account uses {oauthProviderName} sign-in.
                    </p>
                    <p className="leading-relaxed">
                      Password management, multi-factor authentication, and account recovery are securely handled by your {oauthProviderName} provider account.
                    </p>
                  </div>
                )}

                {/* Active Sessions */}
                <div className="pt-4 border-t border-[var(--border-color)] space-y-3">
                  <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                    Active Sessions
                  </h3>
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-500 text-xs">●</span>
                        <span className="text-xs font-bold text-[var(--text-primary)]">Current Session ({browserInfo})</span>
                      </div>
                      <span className="text-[11px] text-[var(--text-muted)] block mt-0.5">
                        JWT Token active (expires in 7 days)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={handleSignOutAllDevices}
                      className="px-3.5 py-1.5 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] transition cursor-pointer"
                    >
                      Sign Out Device
                    </button>
                  </div>
                </div>

                {/* Security Activity & Audit Log (Part 37) */}
                <div className="pt-5 border-t border-[var(--border-color)] space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                        Security Activity & Audit Log
                      </h3>
                      <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                        Chronological record of authentication, schedule modifications, and security actions.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setLoadingAuditLogs(true);
                        api.getAuditLogs(20, 0)
                          .then((res) => setAuditLogs(res.items || []))
                          .catch(() => {})
                          .finally(() => setLoadingAuditLogs(false));
                      }}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
                    >
                      {loadingAuditLogs ? 'Refreshing...' : 'Refresh Activity'}
                    </button>
                  </div>

                  {loadingAuditLogs ? (
                    <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center text-xs text-[var(--text-muted)]">
                      Loading activity records...
                    </div>
                  ) : auditLogs.length === 0 ? (
                    <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center text-xs text-[var(--text-muted)]">
                      No security activity recorded yet.
                    </div>
                  ) : (
                    <div className="divide-y divide-[var(--border-color)] rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] overflow-hidden">
                      {auditLogs.map((item) => (
                        <div key={item.id} className="p-3.5 flex items-start justify-between gap-3 text-xs hover:bg-[var(--bg-card)] transition">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-[var(--text-primary)]">
                                {item.description || item.action}
                              </span>
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 uppercase tracking-wider">
                                {item.action}
                              </span>
                            </div>
                            <span className="text-[11px] text-[var(--text-muted)] block">
                              {new Date(item.created_at).toLocaleString([], {
                                dateStyle: 'medium',
                                timeStyle: 'short',
                              })}
                              {item.ip_address && ` • IP: ${item.ip_address}`}
                            </span>
                          </div>
                          <span className="text-emerald-500 font-bold text-[11px] shrink-0">✓ Verified</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* ------------------------------------------------------------- */}
            {/* 5. DANGER ZONE SECTION */}
            {/* ------------------------------------------------------------- */}
            {activeTab === 'danger' && (
              <section className="bg-red-500/10 border-2 border-red-500/40 rounded-2xl p-5 sm:p-7 shadow-xl space-y-6 animate-fade-in">
                <div className="border-b border-red-500/30 pb-4">
                  <h2 className="text-base sm:text-lg font-black text-red-500 flex items-center gap-2">
                    <span>⚠️</span>
                    <span>Danger Zone</span>
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    Irreversible actions: export full schedule backups or permanently delete your account.
                  </p>
                </div>

                {/* AI Privacy & Transparency Notice (Part 38 & 41) */}
                <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">✦</span>
                    <span className="text-xs font-bold text-[var(--text-primary)]">SyncShift Assistant Privacy & Transparency</span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    SyncShift Assistant acts solely as an interpreter for your natural language schedule queries. Only minimal scheduling context (today's timetable, work hours, active conflicts) is sent for query evaluation. Passwords, JWT secrets, and other users' records are never exposed to AI models. The assistant cannot directly modify your schedule without your explicit manual confirmation.
                  </p>
                </div>

                {/* Export Data */}
                <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Export My Timetable & Data</span>
                    <span className="text-[11px] text-[var(--text-secondary)] block mt-0.5">
                      Download a complete JSON backup of your classes, work shifts, study tasks, and preferences.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleExportData}
                    disabled={exportingData}
                    className="px-4 py-2 rounded-xl bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs font-bold text-[var(--text-primary)] transition flex items-center gap-2 shrink-0 cursor-pointer"
                  >
                    <span>📥</span>
                    <span>{exportingData ? 'Generating Backup...' : 'Export My Data'}</span>
                  </button>
                </div>

                {/* Delete Account */}
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold text-red-500 block">Delete Account</span>
                    <span className="text-[11px] text-[var(--text-secondary)] block mt-0.5">
                      Permanently remove your account, classes, shifts, and study records. This action cannot be reversed.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDeleteModalOpen(true)}
                    className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition shadow-lg shadow-red-950/60 shrink-0 cursor-pointer"
                  >
                    Delete My Account
                  </button>
                </div>
              </section>
            )}
          </div>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--modal-overlay)] backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[var(--bg-card)] border border-red-500/50 rounded-2xl shadow-2xl p-6 space-y-4 animate-fade-in text-[var(--text-primary)]">
            <div className="flex items-center gap-3 text-red-500">
              <span className="text-2xl">⚠️</span>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Delete SyncShift Account?</h3>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              This permanently deletes all your classes, work shifts, study tasks, and schedule data. This cannot be undone.
            </p>

            {/* If email user, ask for password */}
            {user?.has_password && (
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                  Enter Password to Confirm
                </label>
                <input
                  type="password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  placeholder="Your account password"
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-red-500"
                />
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Type <span className="text-red-500 font-mono font-bold">DELETE</span> to confirm
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] focus:outline-none focus:border-red-500 font-mono uppercase"
              />
            </div>

            <div className="pt-3 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setDeleteConfirmText('');
                  setDeletePassword('');
                }}
                className="px-4 py-2 rounded-xl bg-[var(--bg-secondary)] hover:border-[var(--border-hover)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={
                  deletingAccount ||
                  deleteConfirmText.trim() !== 'DELETE' ||
                  (Boolean(user?.has_password) && !deletePassword)
                }
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-40 text-xs font-bold text-white transition shadow-lg shadow-red-950/60 cursor-pointer"
              >
                {deletingAccount ? 'Deleting Account...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SettingsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, status } = useAuthContext();

  useEffect(() => {
    if (status === 'authenticated' && user) {
      const isUniv = ['faculty', 'professor', 'admin', 'super_admin'].includes(
        user.institution_role || ''
      );
      const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
      router.replace((isUniv ? '/university/settings' : '/student/settings') + query);
    }
  }, [user, status, router, searchParams]);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center text-[var(--text-muted)] text-sm">
      Loading Settings...
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center text-[var(--text-muted)] text-sm">Loading Settings...</div>}>
        <SettingsRedirect />
      </Suspense>
    </ProtectedRoute>
  );
}

