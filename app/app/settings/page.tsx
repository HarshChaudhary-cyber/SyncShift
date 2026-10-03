'use client';

import React, { Suspense, useEffect, useMemo, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  UserCircleIcon,
  PaintBrushIcon,
  CalendarDaysIcon,
  BellIcon,
  ShieldCheckIcon,
  ArchiveBoxArrowDownIcon,
  MagnifyingGlassIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  AcademicCapIcon,
  BriefcaseIcon,
  BookOpenIcon,
  ClockIcon,
  EyeIcon,
  EyeSlashIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  BuildingLibraryIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import ProtectedRoute from '@/components/ProtectedRoute';
import TimePicker from '@/components/ui/TimePicker';
import CustomSelect from '@/components/ui/CustomSelect';
import { useAuthContext } from '@/context/AuthContext';
import { useThemeContext } from '@/context/ThemeContext';
import {
  api,
  ApiError,
  NotificationLogItem,
} from '@/lib/api';
import { getBrowserAndOs } from '@/lib/notificationHelpers';
import { TIMEZONE_OPTIONS } from '@/lib/timezones';
import {
  formatTimeDisplay,
  getUserPrefKey,
  applyReducedMotion,
  getPreferencesFromUser,
  ReducedMotionPref,
  TimeFormat,
  WeekStartDay,
  CalendarDefaultView,
} from '@/lib/preferences';
import { isProfessor } from '@/lib/academic';

export type SettingsCategoryKey =
  | 'account'
  | 'appearance'
  | 'calendar'
  | 'notifications'
  | 'security'
  | 'privacy';

interface CategoryDef {
  key: SettingsCategoryKey;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
}

const CATEGORIES: CategoryDef[] = [
  { key: 'account', label: 'Account', description: 'Personal identity, timezone and work limits', icon: UserCircleIcon },
  { key: 'appearance', label: 'Appearance & accessibility', description: 'Theme, reduced motion and display preferences', icon: PaintBrushIcon },
  { key: 'calendar', label: 'Calendar & planner', description: 'Week start, time format, transition buffers and planning hours', icon: CalendarDaysIcon },
  { key: 'notifications', label: 'Notifications', description: 'Push alerts, reminders and quiet hours', icon: BellIcon },
  { key: 'security', label: 'Security', description: 'Password, sign-in methods and recent security activity', icon: ShieldCheckIcon },
  { key: 'privacy', label: 'Privacy & data', description: 'Data export and account deletion', icon: ArchiveBoxArrowDownIcon },
];

const LEGACY_TAB_MAP: Record<string, SettingsCategoryKey> = {
  profile: 'account',
  preferences: 'appearance',
  calendar: 'calendar',
  notifications: 'notifications',
  security: 'security',
  danger: 'privacy',
};

const REMINDER_OPTIONS = [
  { value: 0, label: '0 min (At start)' },
  { value: 15, label: '15 minutes before' },
  { value: 30, label: '30 minutes before' },
  { value: 60, label: '60 minutes (1 hour) before' },
  { value: 120, label: '120 minutes (2 hours) before' },
];

const TRANSITION_BUFFER_OPTIONS = [
  { value: 0, label: '0 minutes (No buffer)' },
  { value: 10, label: '10 minutes' },
  { value: 15, label: '15 minutes (Standard)' },
  { value: 30, label: '30 minutes (Moderate travel)' },
  { value: 45, label: '45 minutes' },
  { value: 60, label: '60 minutes (1 hour travel)' },
];

const SESSION_DURATION_OPTIONS = [
  { value: 25, label: '25 minutes (Pomodoro)' },
  { value: 30, label: '30 minutes' },
  { value: 45, label: '45 minutes (Standard)' },
  { value: 60, label: '60 minutes (1 hour)' },
  { value: 90, label: '90 minutes (Deep focus)' },
  { value: 120, label: '120 minutes (2 hours)' },
];

const BREAK_DURATION_OPTIONS = [
  { value: 5, label: '5 minutes (Short break)' },
  { value: 10, label: '10 minutes' },
  { value: 15, label: '15 minutes (Standard break)' },
  { value: 20, label: '20 minutes' },
  { value: 30, label: '30 minutes (Extended break)' },
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
  { value: 'en', label: 'English (Default)' },
  { value: 'de', label: 'Deutsch (German)' },
  { value: 'hi', label: 'Hindi' },
  { value: 'fr', label: 'Français (French)' },
  { value: 'es', label: 'Español (Spanish)' },
];

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

interface SearchIndexItem {
  id: string;
  title: string;
  category: SettingsCategoryKey;
  keywords: string;
}

const SEARCH_INDEX: SearchIndexItem[] = [
  { id: 'display_name', title: 'Display name & account profile', category: 'account', keywords: 'name profile account user display avatar' },
  { id: 'timezone', title: 'Timezone', category: 'account', keywords: 'time zone iana gmt utc clock local' },
  { id: 'weekly_limit', title: 'Weekly work hours limit', category: 'account', keywords: 'hours job shift weekly balance visa work limit personal' },
  { id: 'theme', title: 'Interface Theme (Dark, Light, System)', category: 'appearance', keywords: 'theme dark light mode color contrast visual appearance' },
  { id: 'reduced_motion', title: 'Reduced motion preference', category: 'appearance', keywords: 'motion animation transition vestibular accessibility visual' },
  { id: 'language', title: 'Language selection', category: 'appearance', keywords: 'language translation english german hindi french spanish localization' },
  { id: 'week_start', title: 'Week starts on (Monday / Sunday)', category: 'calendar', keywords: 'monday sunday calendar week start first day schedule' },
  { id: 'time_format', title: 'Time format (12-hour AM/PM vs 24-hour)', category: 'calendar', keywords: 'time clock 12h 24h am pm military format' },
  { id: 'calendar_view', title: 'Default calendar view mode', category: 'calendar', keywords: 'view week day 7day 5day month schedule default' },
  { id: 'transition_buffer', title: 'Transition travel buffer', category: 'calendar', keywords: 'buffer travel transition travel-aware gap minutes rest' },
  { id: 'planning_hours', title: 'Planning hours window & session duration', category: 'calendar', keywords: 'planner study grading preparation break duration smart hours window' },
  { id: 'push_notifications', title: 'Push notifications & device alerts', category: 'notifications', keywords: 'push alerts bell web browser permission notify device' },
  { id: 'reminders', title: 'Event reminder lead times', category: 'notifications', keywords: 'reminders class shift study deadline conflict alert minutes before lead' },
  { id: 'quiet_hours', title: 'Quiet hours (Do Not Disturb)', category: 'notifications', keywords: 'quiet hours do not disturb sleep dnd mute night' },
  { id: 'password', title: 'Change account password', category: 'security', keywords: 'password credentials security login uppercase length strength' },
  { id: 'audit_logs', title: 'Recent security & sign-in activity', category: 'security', keywords: 'audit activity log history logins sessions ip security' },
  { id: 'export_data', title: 'Export personal schedule data', category: 'privacy', keywords: 'export download backup json data calendar events privacy' },
  { id: 'delete_account', title: 'Delete account permanently', category: 'privacy', keywords: 'delete account erase remove danger zone terminate privacy' },
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

export function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, refreshUser, logout } = useAuthContext();
  const { theme, changeTheme } = useThemeContext();

  // Role detection
  const isSuperAdmin = user?.institution_role === 'super_admin';
  const isProf = isProfessor(user?.institution_role);

  // Active category determination: derived directly from URL with fallback to 'account'
  const activeCategory: SettingsCategoryKey = useMemo(() => {
    const raw = searchParams.get('category') || searchParams.get('tab');
    if (!raw) return 'account';
    if (raw in LEGACY_TAB_MAP) return LEGACY_TAB_MAP[raw];
    const match = CATEGORIES.find((c) => c.key === raw);
    return match ? match.key : 'account';
  }, [searchParams]);

  const selectCategory = (key: SettingsCategoryKey) => {
    router.push(`/settings?category=${key}`);
  };

  // Toast feedback
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error'; id: number } | null>(null);
  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    const id = Date.now();
    setToast({ message, type, id });
    setTimeout(() => {
      setToast(curr => (curr?.id === id ? null : curr));
    }, 4000);
  };

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    return SEARCH_INDEX.filter(item =>
      item.title.toLowerCase().includes(q) || item.keywords.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  // ---------------------------------------------------------------------------
  // ACCOUNT STATE
  // ---------------------------------------------------------------------------
  const [displayName, setDisplayName] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [timezone, setTimezone] = useState('Europe/London');
  const [weeklyLimit, setWeeklyLimit] = useState<number>(20);
  const [savingAccount, setSavingAccount] = useState(false);
  const [tzSearch, setTzSearch] = useState('');
  const [tzDropdownOpen, setTzDropdownOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // APPEARANCE & ACCESSIBILITY STATE
  // ---------------------------------------------------------------------------
  const [reducedMotion, setReducedMotion] = useState<ReducedMotionPref>('system');
  const [language, setLanguage] = useState('en');
  const [savingAppearance, setSavingAppearance] = useState(false);

  // ---------------------------------------------------------------------------
  // CALENDAR & PLANNER STATE
  // ---------------------------------------------------------------------------
  const [currency, setCurrency] = useState('INR');
  const [weekStartsOn, setWeekStartsOn] = useState<WeekStartDay>('monday');
  const [timeFormat, setTimeFormat] = useState<TimeFormat>('12h');
  const [defaultCalendarView, setDefaultCalendarView] = useState<CalendarDefaultView>('7day');
  const [minimumTransitionMinutes, setMinimumTransitionMinutes] = useState<number>(15);
  const [planningHoursStart, setPlanningHoursStart] = useState<number>(9);
  const [planningHoursEnd, setPlanningHoursEnd] = useState<number>(18);
  const [preferredSessionDuration, setPreferredSessionDuration] = useState<number>(45);
  const [preferredBreakDuration, setPreferredBreakDuration] = useState<number>(15);
  const [savingCalendar, setSavingCalendar] = useState(false);

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
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [browserInfo, setBrowserInfo] = useState('Browser');

  // ---------------------------------------------------------------------------
  // SECURITY & AUDIT STATE
  // ---------------------------------------------------------------------------
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAuditLogs, setLoadingAuditLogs] = useState(false);

  // ---------------------------------------------------------------------------
  // PRIVACY & DATA STATE
  // ---------------------------------------------------------------------------
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deletePassword, setDeletePassword] = useState('');
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [exportingData, setExportingData] = useState(false);

  // Populate from authenticated user profile
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || user.email.split('@')[0]);
      setAvatarUrl(user.avatar_url || '');
      setTimezone(user.timezone || 'Europe/London');
      setWeeklyLimit(user.weekly_work_hour_limit ?? 20);
      setCurrency(user.currency || 'INR');
      setLanguage(user.language || 'en');
      setMinimumTransitionMinutes(user.minimum_transition_minutes ?? 15);

      const prefs = getPreferencesFromUser(user);
      setWeekStartsOn(prefs.week_starts_on);
      setTimeFormat(prefs.time_format);
      setDefaultCalendarView(prefs.default_calendar_view);
      setReducedMotion(prefs.reduced_motion);
      applyReducedMotion(prefs.reduced_motion);
      setPlanningHoursStart(prefs.planning_hours_start);
      setPlanningHoursEnd(prefs.planning_hours_end);
      setPreferredSessionDuration(prefs.preferred_session_duration);
      setPreferredBreakDuration(prefs.preferred_break_duration);

      if (user.theme) {
        changeTheme(user.theme as any);
      }
    }

    if (typeof window !== 'undefined') {
      setBrowserInfo(getBrowserAndOs());
      if ('Notification' in window) {
        setPermission(Notification.permission);
      }
    }
  }, [user]);

  // Load audit logs when security category active
  useEffect(() => {
    if (activeCategory === 'security' && user) {
      setLoadingAuditLogs(true);
      api.getAuditLogs(15, 0)
        .then(res => setAuditLogs(res.items || []))
        .catch(() => {})
        .finally(() => setLoadingAuditLogs(false));
    }
  }, [activeCategory, user]);

  // Load notification preferences
  useEffect(() => {
    if (activeCategory === 'notifications' && user) {
      setNotifLoading(true);
      Promise.all([
        api.getNotificationPrefs(),
        api.getNotificationLog(false).catch(() => []),
      ])
        .then(([prefs, logs]) => {
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
        })
        .catch(err => {
          console.error('Failed to load notifications:', err);
        })
        .finally(() => setNotifLoading(false));
    }
  }, [activeCategory, user]);

  // Timezones list
  const allTimezones = useMemo(() => {
    let list = [...POPULAR_TIMEZONES];
    if (typeof Intl !== 'undefined' && typeof (Intl as any).supportedValuesOf === 'function') {
      try {
        const supported = (Intl as any).supportedValuesOf('timeZone');
        list = Array.from(new Set([...list, ...supported]));
      } catch {}
    }
    return list;
  }, []);

  const filteredTimezones = useMemo(() => {
    if (!tzSearch.trim()) return allTimezones.slice(0, 30);
    const q = tzSearch.toLowerCase();
    return allTimezones.filter(tz => tz.toLowerCase().includes(q)).slice(0, 30);
  }, [allTimezones, tzSearch]);

  // Password complexity checks
  const passwordHasLength = newPassword.length >= 8;
  const passwordHasUpper = /[A-Z]/.test(newPassword);
  const passwordHasNumber = /\d/.test(newPassword);
  const isPasswordValid = passwordHasLength && passwordHasUpper && passwordHasNumber;
  const doPasswordsMatch = newPassword === confirmPassword;

  // Account provider label
  const oauthProviderName = useMemo(() => {
    if (user?.oauth_provider === 'google') return 'Google Workspace';
    if (user?.oauth_provider === 'microsoft') return 'Microsoft 365 / Entra ID';
    if (user?.oauth_provider === 'facebook') return 'Facebook';
    if (user?.oauth_provider === 'apple') return 'Apple ID';
    return user?.has_password ? 'Email & Password' : 'Institutional Single Sign-On';
  }, [user]);

  // Handlers
  const handleSaveAccount = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSavingAccount(true);
      await api.updateProfile({
        display_name: displayName.trim(),
        timezone,
        weekly_work_hour_limit: Number(weeklyLimit),
        avatar_url: avatarUrl.trim() || null,
      });
      await refreshUser();
      showToast('Account details saved successfully', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save account profile', 'error');
    } finally {
      setSavingAccount(false);
    }
  };

  const handleSaveAppearance = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSavingAppearance(true);
      applyReducedMotion(reducedMotion);
      if (user) {
        localStorage.setItem(getUserPrefKey(user.user_id, 'reduced_motion'), reducedMotion);
      }
      await api.updateProfile({
        theme,
        reduced_motion: reducedMotion,
        language,
      });
      await refreshUser();
      showToast('Appearance preferences saved', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save appearance', 'error');
    } finally {
      setSavingAppearance(false);
    }
  };

  const handleSaveCalendar = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (planningHoursStart > planningHoursEnd) {
      showToast('Planning window start hour cannot be after end hour', 'error');
      return;
    }
    try {
      setSavingCalendar(true);
      if (user) {
        localStorage.setItem(getUserPrefKey(user.user_id, 'week_starts_on'), weekStartsOn);
        localStorage.setItem(getUserPrefKey(user.user_id, 'time_format'), timeFormat);
        localStorage.setItem(getUserPrefKey(user.user_id, 'default_calendar_view'), defaultCalendarView);
      }
      await api.updateProfile({
        currency,
        week_starts_on: weekStartsOn,
        time_format: timeFormat,
        default_calendar_view: defaultCalendarView,
        minimum_transition_minutes: Number(minimumTransitionMinutes),
        planning_hours_start: Number(planningHoursStart),
        planning_hours_end: Number(planningHoursEnd),
        preferred_session_duration: Number(preferredSessionDuration),
        preferred_break_duration: Number(preferredBreakDuration),
      });
      await refreshUser();
      window.dispatchEvent(new CustomEvent('syncshift:schedule-updated'));
      showToast('Calendar & planner preferences saved', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save calendar preferences', 'error');
    } finally {
      setSavingCalendar(false);
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
      showToast('Notification settings saved', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save notification preferences', 'error');
    } finally {
      setSavingNotifs(false);
    }
  };

  const handleRequestPushPermission = async () => {
    if (!('Notification' in window)) {
      showToast('Push notifications are not supported by this browser', 'error');
      return;
    }
    try {
      const res = await Notification.requestPermission();
      setPermission(res);
      if (res === 'granted') {
        showToast('Push notifications enabled for this device', 'success');
      } else {
        showToast('Notification permission was declined', 'error');
      }
    } catch {
      showToast('Failed to request notification permission', 'error');
    }
  };

  const handleSendTestNotification = async () => {
    try {
      setTestSending(true);
      const res = await api.sendTestNotification();
      showToast(res.message || 'Test notification dispatched', 'success');
    } catch (err: any) {
      showToast(err.message || 'Could not dispatch test notification', 'error');
    } finally {
      setTestSending(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isPasswordValid || !doPasswordsMatch) {
      showToast('Please check password requirements', 'error');
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
      showToast('Password changed successfully', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to update password', 'error');
    } finally {
      setSavingPassword(false);
    }
  };

  const handleExportData = async () => {
    try {
      setExportingData(true);
      const data = await api.exportPrivacyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `syncshift-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      showToast('Personal calendar data exported', 'success');
    } catch (err: any) {
      showToast(err.message || 'Export failed. Please try again.', 'error');
    } finally {
      setExportingData(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      showToast('Type DELETE to confirm permanent deletion', 'error');
      return;
    }
    try {
      setDeletingAccount(true);
      await api.deleteAccount({
        password: deletePassword || undefined,
        confirm: 'DELETE',
      });
      setDeleteModalOpen(false);
      logout();
    } catch (err: any) {
      showToast(err.message || 'Account deletion failed', 'error');
      setDeletingAccount(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Toast Announcement */}
      {toast && (
        <div
          role="status"
          className={`notice ${toast.type === 'error' ? 'error' : ''}`}
          style={{ position: 'sticky', top: 12, zIndex: 50 }}
        >
          <span>{toast.message}</span>
          <button type="button" aria-label="Dismiss notification" onClick={() => setToast(null)}>
            <XMarkIcon className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Header and Search */}
      <header className="ws-header">
        <div>
          <div className="ws-kicker">Workspace Preferences</div>
          <h1>Settings & Preferences</h1>
          <p className="ws-muted">
            Configure your {isProf ? 'teaching schedule and academic workspace' : isSuperAdmin ? 'system administrator account' : 'study and personal routine'}.
          </p>
        </div>

        {/* Search bar */}
        <div style={{ position: 'relative', width: 'min(100%, 320px)' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Search settings..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSearchOpen(Boolean(e.target.value.trim()));
              }}
              onFocus={() => setSearchOpen(Boolean(searchQuery.trim()))}
              className="ws-input"
              style={{
                width: '100%',
                paddingLeft: 34,
                paddingRight: searchQuery ? 30 : 12,
                height: 38,
                borderRadius: 8,
                fontSize: 13,
                border: '1px solid var(--border-color)',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
              }}
            />
            <MagnifyingGlassIcon
              className="w-4 h-4"
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: 10,
                top: 11,
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            {searchQuery && (
              <button
                type="button"
                aria-label="Clear search query"
                onClick={() => {
                  setSearchQuery('');
                  setSearchOpen(false);
                }}
                style={{
                  position: 'absolute',
                  right: 8,
                  top: 9,
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                }}
              >
                <XMarkIcon className="w-4 h-4" aria-hidden="true" />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {searchOpen && (
            <div
              style={{
                position: 'absolute',
                top: 44,
                right: 0,
                left: 0,
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                zIndex: 60,
                maxHeight: 280,
                overflowY: 'auto',
                padding: 6,
              }}
            >
              {searchResults.length === 0 ? (
                <div style={{ padding: '12px 14px', fontSize: 12, color: 'var(--text-muted)' }}>
                  No settings matching &ldquo;{searchQuery}&rdquo;. Try &ldquo;theme&rdquo;, &ldquo;timezone&rdquo;, or &ldquo;notifications&rdquo;.
                </div>
              ) : (
                searchResults.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      selectCategory(item.category);
                      setSearchOpen(false);
                      setSearchQuery('');
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: 6,
                      border: 'none',
                      background: 'none',
                      textAlign: 'left',
                      fontSize: 12,
                      color: 'var(--text-primary)',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-secondary)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                  >
                    <span>{item.title}</span>
                    <span className="ws-badge" style={{ fontSize: 10 }}>
                      {CATEGORIES.find((c) => c.key === item.category)?.label}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </header>

      {/* Category Navigation Bar */}
      <nav
        aria-label="Settings Categories"
        className="ws-tabs"
        style={{
          display: 'flex',
          gap: 12,
          overflowX: 'auto',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: 2,
        }}
      >
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => selectCategory(cat.key)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 14px',
                borderRadius: '8px 8px 0 0',
                border: 'none',
                borderBottom: isActive ? '2px solid #818cf8' : '2px solid transparent',
                background: isActive ? 'var(--bg-secondary)' : 'none',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 500,
                fontSize: 13,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <Icon className="w-4 h-4" aria-hidden="true" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </nav>

      {/* =================================================================== */}
      {/* 1. ACCOUNT CATEGORY                                                 */}
      {/* =================================================================== */}
      {activeCategory === 'account' && (
        <div className="space-y-6">
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Account Profile</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Identity and personal planning parameters for {user?.email}
                </p>
              </div>
              <span className="ws-badge accent">
                {isSuperAdmin ? 'Super Administrator' : isProf ? 'Professor / Instructor' : 'Student Account'}
              </span>
            </div>

            <form onSubmit={handleSaveAccount} className="ws-form">
              <div className="ws-form-row">
                <label>
                  <span>Display Name</span>
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    required
                  />
                </label>
                <label>
                  <span>Email address (Authoritative sign-in identifier)</span>
                  <input
                    type="text"
                    value={user?.email || ''}
                    disabled
                    style={{ opacity: 0.7, cursor: 'not-allowed' }}
                  />
                </label>
              </div>

              <div className="ws-form-row">
                <label>
                  <span>Avatar photo URL</span>
                  <input
                    type="url"
                    placeholder="https://example.com/avatar.jpg"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                  />
                </label>
                <label>
                  <span>Primary Timezone</span>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="text"
                      value={tzSearch || timezone}
                      placeholder="Search timezone..."
                      onChange={(e) => {
                        setTzSearch(e.target.value);
                        setTzDropdownOpen(true);
                      }}
                      onFocus={() => setTzDropdownOpen(true)}
                    />
                    {tzDropdownOpen && (
                      <div
                        style={{
                          position: 'absolute',
                          top: '100%',
                          left: 0,
                          right: 0,
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border-color)',
                          borderRadius: 8,
                          boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                          maxHeight: 200,
                          overflowY: 'auto',
                          zIndex: 50,
                          marginTop: 4,
                        }}
                      >
                        {filteredTimezones.map((tz) => (
                          <button
                            key={tz}
                            type="button"
                            onClick={() => {
                              setTimezone(tz);
                              setTzSearch('');
                              setTzDropdownOpen(false);
                            }}
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              width: '100%',
                              padding: '8px 12px',
                              border: 'none',
                              background: tz === timezone ? 'var(--bg-secondary)' : 'none',
                              color: 'var(--text-primary)',
                              fontSize: 12,
                              textAlign: 'left',
                            }}
                          >
                            <span>{tz}</span>
                            <span style={{ color: 'var(--text-muted)' }}>{getTimezoneOffsetString(tz)}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </label>
              </div>

              {/* Weekly work hour limit with disclaimer */}
              <div
                style={{
                  padding: 16,
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-secondary)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <ClockIcon className="w-5 h-5" style={{ color: '#818cf8' }} aria-hidden="true" />
                  <strong style={{ fontSize: 13 }}>Weekly work limit planning preference</strong>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                  Set your target weekly work limit (0–168 hrs). SyncShift uses this value to calculate your remaining hours and highlight schedule overruns.
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <input
                    type="number"
                    min={0}
                    max={168}
                    step={0.5}
                    value={weeklyLimit}
                    onChange={(e) => setWeeklyLimit(parseFloat(e.target.value) || 0)}
                    style={{ width: 120 }}
                  />
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>hours per week</span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                    marginTop: 12,
                    fontSize: 11,
                    color: 'var(--text-muted)',
                  }}
                >
                  <ExclamationTriangleIcon className="w-4 h-4 shrink-0 text-amber-500" aria-hidden="true" />
                  <span>
                    Disclaimer: Weekly work limits are personal planning guidelines and do not constitute guaranteed legal or visa compliance counsel.
                  </span>
                </div>
              </div>

              {/* Links to academic profile / super admin */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: 12,
                  borderTop: '1px solid var(--border-color)',
                }}
              >
                <Link
                  href="/profile"
                  className="ws-link"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}
                >
                  <ArrowTopRightOnSquareIcon className="w-4 h-4" aria-hidden="true" />
                  <span>Edit public academic profile & office hours</span>
                </Link>

                <button type="submit" disabled={savingAccount} className="ws-button primary">
                  {savingAccount ? (
                    <>
                      <ArrowPathIcon className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save account details</span>
                  )}
                </button>
              </div>
            </form>
          </section>

          {/* Super Admin institutional policy link */}
          {isSuperAdmin && (
            <section className="ws-panel" style={{ borderColor: 'rgba(99,102,241,0.4)' }}>
              <div className="ws-panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BuildingLibraryIcon className="w-5 h-5 text-indigo-400" aria-hidden="true" />
                  <h2>Institutional Administration</h2>
                </div>
                <span className="ws-badge accent">University Policy</span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                You have super-administrator privileges. Institutional policies, user roles, baseline timetables, and audit history are managed in dedicated administration interfaces.
              </p>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <Link href="/admin" className="ws-button primary">
                  Open University Administration
                </Link>
                <Link href="/university/settings" className="ws-button">
                  Institutional Settings
                </Link>
              </div>
            </section>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* 2. APPEARANCE & ACCESSIBILITY                                       */}
      {/* =================================================================== */}
      {activeCategory === 'appearance' && (
        <div className="space-y-6">
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Appearance & Accessibility</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Theme contrast, animation preferences, and interface language
                </p>
              </div>
            </div>

            <form onSubmit={handleSaveAppearance} className="ws-form">
              {/* Theme Selector */}
              <div>
                <label style={{ marginBottom: 10 }}>
                  <span style={{ fontWeight: 600 }}>Color Theme</span>
                </label>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: 12,
                  }}
                >
                  {[
                    { key: 'dark', label: 'Dark Mode', icon: MoonIcon },
                    { key: 'light', label: 'Light Mode', icon: SunIcon },
                    { key: 'system', label: 'System Default', icon: ComputerDesktopIcon },
                  ].map((item) => {
                    const Icon = item.icon;
                    const isSelected = theme === item.key;
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => changeTheme(item.key as any)}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: 8,
                          padding: 16,
                          borderRadius: 8,
                          border: isSelected ? '2px solid #818cf8' : '1px solid var(--border-color)',
                          background: isSelected ? 'rgba(99,102,241,0.1)' : 'var(--bg-secondary)',
                          color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                          cursor: 'pointer',
                        }}
                      >
                        <Icon className="w-6 h-6" style={{ color: isSelected ? '#818cf8' : 'var(--text-muted)' }} aria-hidden="true" />
                        <span style={{ fontSize: 12, fontWeight: 550 }}>{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Reduced Motion Selector */}
              <div style={{ marginTop: 12 }}>
                <label style={{ marginBottom: 10 }}>
                  <span style={{ fontWeight: 600 }}>Reduced Motion & Transitions</span>
                </label>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                  Minimizes motion effects, card transitions, and slide animations for users sensitive to vestibular motion.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
                  {[
                    { key: 'system', label: 'Follow OS preference' },
                    { key: 'reduced', label: 'Always reduced motion' },
                    { key: 'normal', label: 'Standard animations' },
                  ].map((opt) => (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => {
                        setReducedMotion(opt.key as ReducedMotionPref);
                        applyReducedMotion(opt.key as ReducedMotionPref);
                      }}
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        border: reducedMotion === opt.key ? '2px solid #818cf8' : '1px solid var(--border-color)',
                        background: reducedMotion === opt.key ? 'rgba(99,102,241,0.1)' : 'var(--bg-secondary)',
                        color: reducedMotion === opt.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: 'pointer',
                        textAlign: 'center',
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language selection notice */}
              <div style={{ marginTop: 12 }}>
                <label>
                  <span>Language Preference</span>
                  <CustomSelect
                    value={language}
                    onChange={(v) => setLanguage(v)}
                    options={LANGUAGE_OPTIONS}
                  />
                </label>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                  Note: SyncShift interface is currently provided in English. Selected language preference is preserved for upcoming internationalization releases.
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 12 }}>
                <button type="submit" disabled={savingAppearance} className="ws-button primary">
                  {savingAppearance ? 'Saving...' : 'Save appearance'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {/* =================================================================== */}
      {/* 3. CALENDAR & PLANNER                                               */}
      {/* =================================================================== */}
      {activeCategory === 'calendar' && (
        <div className="space-y-6">
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Calendar Display & Planning Preferences</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Customize week structure, clock format, buffers, and planning windows
                </p>
              </div>
            </div>

            <form onSubmit={handleSaveCalendar} className="ws-form">
              {/* Week Starts On */}
              <div className="ws-form-row">
                <label>
                  <span style={{ fontWeight: 600 }}>Week Starts On</span>
                  <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                    {[
                      { key: 'monday', label: 'Monday (Academic ISO)' },
                      { key: 'sunday', label: 'Sunday' },
                    ].map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => setWeekStartsOn(item.key as WeekStartDay)}
                        style={{
                          flex: 1,
                          padding: 10,
                          borderRadius: 8,
                          border: weekStartsOn === item.key ? '2px solid #818cf8' : '1px solid var(--border-color)',
                          background: weekStartsOn === item.key ? 'rgba(99,102,241,0.1)' : 'var(--bg-secondary)',
                          color: weekStartsOn === item.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: 12,
                          fontWeight: 500,
                          cursor: 'pointer',
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </label>

                {/* Time format (12h vs 24h) */}
                <label>
                  <span style={{ fontWeight: 600 }}>Time Format</span>
                  <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                    {[
                      { key: '12h', label: '12-Hour (e.g. 2:30 PM)' },
                      { key: '24h', label: '24-Hour (e.g. 14:30)' },
                    ].map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => setTimeFormat(item.key as TimeFormat)}
                        style={{
                          flex: 1,
                          padding: 10,
                          borderRadius: 8,
                          border: timeFormat === item.key ? '2px solid #818cf8' : '1px solid var(--border-color)',
                          background: timeFormat === item.key ? 'rgba(99,102,241,0.1)' : 'var(--bg-secondary)',
                          color: timeFormat === item.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: 12,
                          fontWeight: 500,
                          cursor: 'pointer',
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </label>
              </div>

              {/* Default Calendar View & Transition Buffer */}
              <div className="ws-form-row">
                <label>
                  <span>Default Calendar View</span>
                  <CustomSelect
                    value={defaultCalendarView}
                    onChange={(v) => setDefaultCalendarView(v as CalendarDefaultView)}
                    options={[
                      { value: '7day', label: 'Week View (7 days)' },
                      { value: '5day', label: 'Work Week (5 days)' },
                    ]}
                  />
                </label>

                <label>
                  <span>Minimum Transition Buffer Between Events</span>
                  <CustomSelect
                    value={minimumTransitionMinutes}
                    onChange={(v) => setMinimumTransitionMinutes(Number(v))}
                    options={TRANSITION_BUFFER_OPTIONS}
                  />
                </label>
              </div>

              {/* Currency */}
              <div>
                <label>
                  <span>Preferred Currency for Work Wages</span>
                  <CustomSelect
                    value={currency}
                    onChange={(v) => setCurrency(v)}
                    options={CURRENCY_OPTIONS}
                  />
                </label>
              </div>

              {/* Planner Preferences (Adapted to role) */}
              <div
                style={{
                  padding: 16,
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-secondary)',
                  marginTop: 12,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <ClockIcon className="w-5 h-5 text-indigo-400" aria-hidden="true" />
                  <strong style={{ fontSize: 13 }}>
                    {isProf ? 'Teaching Preparation & Planning Windows' : 'Study Sessions & Smart Planner Defaults'}
                  </strong>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>
                  {isProf
                    ? 'Default block sizes for lecture preparation, grading, and office hours.'
                    : 'Target duration and breaks for automated study schedule placement.'}
                </p>

                <div className="ws-form-row">
                  <label>
                    <span>{isProf ? 'Preparation Block Duration' : 'Study Session Duration'}</span>
                    <CustomSelect
                      value={preferredSessionDuration}
                      onChange={(v) => setPreferredSessionDuration(Number(v))}
                      options={SESSION_DURATION_OPTIONS}
                    />
                  </label>
                  <label>
                    <span>{isProf ? 'Break Between Preparation Blocks' : 'Break Between Study Sessions'}</span>
                    <CustomSelect
                      value={preferredBreakDuration}
                      onChange={(v) => setPreferredBreakDuration(Number(v))}
                      options={BREAK_DURATION_OPTIONS}
                    />
                  </label>
                </div>

                <div className="ws-form-row" style={{ marginTop: 12 }}>
                  <label>
                    <span>Daily Planning Window Start Hour</span>
                    <select
                      value={planningHoursStart}
                      onChange={(e) => setPlanningHoursStart(Number(e.target.value))}
                    >
                      {Array.from({ length: 24 }).map((_, h) => (
                        <option key={h} value={h}>
                          {formatTimeDisplay(`${h.toString().padStart(2, '0')}:00`, timeFormat)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Daily Planning Window End Hour</span>
                    <select
                      value={planningHoursEnd}
                      onChange={(e) => setPlanningHoursEnd(Number(e.target.value))}
                    >
                      {Array.from({ length: 24 }).map((_, h) => (
                        <option key={h} value={h}>
                          {formatTimeDisplay(`${h.toString().padStart(2, '0')}:00`, timeFormat)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 12 }}>
                <button type="submit" disabled={savingCalendar} className="ws-button primary">
                  {savingCalendar ? 'Saving...' : 'Save calendar preferences'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {/* =================================================================== */}
      {/* 4. NOTIFICATIONS                                                    */}
      {/* =================================================================== */}
      {activeCategory === 'notifications' && (
        <div className="space-y-6">
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Notifications & Event Reminders</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Configure web push alerts, lead times, and quiet hours
                </p>
              </div>
              <button
                type="button"
                onClick={handleSendTestNotification}
                disabled={testSending}
                className="ws-button"
              >
                {testSending ? 'Sending...' : 'Send test alert'}
              </button>
            </div>

            {notifLoading ? (
              <p role="status">Loading notification settings...</p>
            ) : (
              <form onSubmit={handleSaveNotifications} className="ws-form">
                {/* Push and Browser Permission */}
                <div
                  style={{
                    padding: 16,
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ fontSize: 13, display: 'block' }}>Browser Web Push Alerts</strong>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Status on {browserInfo}: {permission === 'granted' ? 'Allowed' : permission === 'denied' ? 'Blocked by browser' : 'Prompt required'}
                      </span>
                    </div>
                    {permission !== 'granted' ? (
                      <button
                        type="button"
                        onClick={handleRequestPushPermission}
                        className="ws-button primary"
                        style={{ fontSize: 12, padding: '6px 12px' }}
                      >
                        Enable browser push
                      </button>
                    ) : (
                      <span className="ws-badge accent">
                        <CheckCircleIcon className="w-3.5 h-3.5" aria-hidden="true" />
                        Enabled
                      </span>
                    )}
                  </div>
                </div>

                {/* Notification Toggles */}
                <div className="ws-form-row">
                  <label className="ws-check">
                    <input
                      type="checkbox"
                      checked={pushEnabled}
                      onChange={(e) => setPushEnabled(e.target.checked)}
                    />
                    <span>Receive in-app & web push notifications</span>
                  </label>
                  <label className="ws-check">
                    <input
                      type="checkbox"
                      checked={emailEnabled}
                      onChange={(e) => setEmailEnabled(e.target.checked)}
                    />
                    <span>Receive daily email digest summaries</span>
                  </label>
                </div>

                <div className="ws-form-row">
                  <label className="ws-check">
                    <input
                      type="checkbox"
                      checked={conflictAlerts}
                      onChange={(e) => setConflictAlerts(e.target.checked)}
                    />
                    <span>Immediate schedule conflict notifications</span>
                  </label>
                  <label className="ws-check">
                    <input
                      type="checkbox"
                      checked={deadlineReminder}
                      onChange={(e) => setDeadlineReminder(e.target.checked)}
                    />
                    <span>Deadline & assignment approach warnings</span>
                  </label>
                </div>

                {/* Reminder Lead Times */}
                <div style={{ marginTop: 12 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Event Reminder Lead Times</h3>
                  <div className="ws-form-row">
                    <label>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <AcademicCapIcon className="w-4 h-4 text-blue-400" aria-hidden="true" />
                        Class Timetable Reminders
                      </span>
                      <CustomSelect
                        value={classReminderMin}
                        onChange={(v) => setClassReminderMin(Number(v))}
                        options={REMINDER_OPTIONS}
                      />
                    </label>

                    <label>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <BriefcaseIcon className="w-4 h-4 text-emerald-400" aria-hidden="true" />
                        Work Shift Reminders
                      </span>
                      <CustomSelect
                        value={shiftReminderMin}
                        onChange={(v) => setShiftReminderMin(Number(v))}
                        options={REMINDER_OPTIONS}
                      />
                    </label>
                  </div>

                  <div className="ws-form-row" style={{ marginTop: 12 }}>
                    <label>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <BookOpenIcon className="w-4 h-4 text-purple-400" aria-hidden="true" />
                        {isProf ? 'Preparation Block Reminders' : 'Study Session Reminders'}
                      </span>
                      <CustomSelect
                        value={studyReminderMin}
                        onChange={(v) => setStudyReminderMin(Number(v))}
                        options={REMINDER_OPTIONS}
                      />
                    </label>
                  </div>
                </div>

                {/* Quiet Hours */}
                <div
                  style={{
                    padding: 16,
                    borderRadius: 8,
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                    marginTop: 12,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div>
                      <strong style={{ fontSize: 13 }}>Quiet Hours (Do Not Disturb)</strong>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Mutes non-critical reminder notifications during your sleep or rest hours.
                      </p>
                    </div>
                    <label className="ws-check" style={{ cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={quietHoursEnabled}
                        onChange={(e) => setQuietHoursEnabled(e.target.checked)}
                      />
                      <span>Enable</span>
                    </label>
                  </div>

                  {quietHoursEnabled && (
                    <div className="ws-form-row">
                      <label>
                        <span>Quiet Hours Start</span>
                        <TimePicker
                          value={quietHoursStart}
                          onChange={(v) => setQuietHoursStart(v)}
                        />
                      </label>
                      <label>
                        <span>Quiet Hours End</span>
                        <TimePicker
                          value={quietHoursEnd}
                          onChange={(v) => setQuietHoursEnd(v)}
                        />
                      </label>
                    </div>
                  )}
                </div>

                {/* Recent notification logs */}
                {recentLogs.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
                      Recent Notification Delivery Activity
                    </h3>
                    <div className="ws-scroll">
                      <table className="ws-table">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Title</th>
                            <th>Channel</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {recentLogs.map((log) => (
                            <tr key={log.id}>
                              <td>{new Date(log.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                              <td>{log.title}</td>
                              <td>{log.channel}</td>
                              <td>
                                <span className="ws-badge" style={{ fontSize: 10 }}>
                                  {log.delivery_status || 'Sent'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 12 }}>
                  <button type="submit" disabled={savingNotifs} className="ws-button primary">
                    {savingNotifs ? 'Saving...' : 'Save notification settings'}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}

      {/* =================================================================== */}
      {/* 5. SECURITY                                                         */}
      {/* =================================================================== */}
      {activeCategory === 'security' && (
        <div className="space-y-6">
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Account Credentials & Authentication</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Manage login password and check connected identity providers
                </p>
              </div>
              <span className="ws-badge">
                Auth Method: {oauthProviderName}
              </span>
            </div>

            {/* Change Password */}
            {user?.has_password ? (
              <form onSubmit={handleChangePassword} className="ws-form">
                <label>
                  <span>Current Password</span>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      style={{
                        position: 'absolute',
                        right: 10,
                        top: 10,
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {showCurrentPassword ? (
                        <EyeSlashIcon className="w-4 h-4" aria-hidden="true" />
                      ) : (
                        <EyeIcon className="w-4 h-4" aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </label>

                <div className="ws-form-row">
                  <label>
                    <span>New Password</span>
                    <div style={{ position: 'relative' }}>
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                      />
                      <button
                        type="button"
                        aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        style={{
                          position: 'absolute',
                          right: 10,
                          top: 10,
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-muted)',
                        }}
                      >
                        {showNewPassword ? (
                          <EyeSlashIcon className="w-4 h-4" aria-hidden="true" />
                        ) : (
                          <EyeIcon className="w-4 h-4" aria-hidden="true" />
                        )}
                      </button>
                    </div>
                  </label>

                  <label>
                    <span>Confirm New Password</span>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </label>
                </div>

                {/* Password validation indicators */}
                <div style={{ fontSize: 12, display: 'flex', gap: 16, color: 'var(--text-muted)' }}>
                  <span style={{ color: passwordHasLength ? '#34b7a0' : 'inherit' }}>
                    {passwordHasLength ? '✓' : '○'} 8+ characters
                  </span>
                  <span style={{ color: passwordHasUpper ? '#34b7a0' : 'inherit' }}>
                    {passwordHasUpper ? '✓' : '○'} 1 uppercase letter
                  </span>
                  <span style={{ color: passwordHasNumber ? '#34b7a0' : 'inherit' }}>
                    {passwordHasNumber ? '✓' : '○'} 1 number
                  </span>
                  {confirmPassword && (
                    <span style={{ color: doPasswordsMatch ? '#34b7a0' : '#e87986' }}>
                      {doPasswordsMatch ? '✓ Passwords match' : '✕ Passwords do not match'}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 8 }}>
                  <button
                    type="submit"
                    disabled={savingPassword || !isPasswordValid || !doPasswordsMatch}
                    className="ws-button primary"
                  >
                    {savingPassword ? 'Updating...' : 'Update password'}
                  </button>
                </div>
              </form>
            ) : (
              <div
                style={{
                  padding: 16,
                  borderRadius: 8,
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-secondary)',
                  fontSize: 13,
                  color: 'var(--text-secondary)',
                }}
              >
                Your account signs in securely using {oauthProviderName}. Password change is managed through your external identity provider.
              </div>
            )}
          </section>

          {/* Audit Logs */}
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Recent Security & Session Activity</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Audited access events, sign-in attempts, and setting updates
                </p>
              </div>
            </div>

            {loadingAuditLogs ? (
              <p role="status">Loading security activity logs...</p>
            ) : auditLogs.length === 0 ? (
              <p className="ws-muted" style={{ fontSize: 12 }}>No recent audited security events recorded.</p>
            ) : (
              <div className="ws-scroll">
                <table className="ws-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Description</th>
                      <th>IP Address</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td>{new Date(log.created_at).toLocaleString()}</td>
                        <td>
                          <span className="ws-badge" style={{ fontSize: 10 }}>{log.action}</span>
                        </td>
                        <td>{log.description}</td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{log.ip_address || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* =================================================================== */}
      {/* 6. PRIVACY & DATA                                                   */}
      {/* =================================================================== */}
      {activeCategory === 'privacy' && (
        <div className="space-y-6">
          {/* Data Export */}
          <section className="ws-panel">
            <div className="ws-panel-header">
              <div>
                <h2>Personal Schedule Data Export</h2>
                <p className="ws-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Download a complete backup archive of your private work shifts, study tasks, and calendar overrides
                </p>
              </div>
              <button
                type="button"
                onClick={handleExportData}
                disabled={exportingData}
                className="ws-button"
              >
                <ArrowDownTrayIcon className="w-4 h-4" aria-hidden="true" />
                <span>{exportingData ? 'Generating export...' : 'Export JSON'}</span>
              </button>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Export includes personal blocks, recurrence patterns, task completion logs, and conflict settings in standard JSON format.
            </p>
          </section>

          {/* Account Deletion Danger Zone */}
          <section className="ws-panel" style={{ borderColor: 'rgba(232, 121, 134, 0.4)' }}>
            <div className="ws-panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ExclamationTriangleIcon className="w-5 h-5 text-rose-500" aria-hidden="true" />
                <h2 style={{ color: '#e87986' }}>Danger Zone: Delete Account</h2>
              </div>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
              Deleting your account permanently anonymizes your personal schedule data, unlinks enrollments, and cancels ongoing recurring shifts. This action cannot be reversed.
            </p>
            <button
              type="button"
              onClick={() => setDeleteModalOpen(true)}
              className="ws-button danger"
            >
              <TrashIcon className="w-4 h-4" aria-hidden="true" />
              <span>Delete my SyncShift account</span>
            </button>
          </section>
        </div>
      )}

      {/* Account Deletion Modal */}
      {deleteModalOpen && (
        <div className="ws-modal" role="dialog" aria-modal="true" aria-labelledby="delete-account-title">
          <section>
            <header>
              <h2 id="delete-account-title" style={{ color: '#e87986', fontSize: 18, fontWeight: 600 }}>
                Confirm Account Deletion
              </h2>
              <button
                type="button"
                aria-label="Close modal"
                onClick={() => setDeleteModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}
              >
                <XMarkIcon className="w-5 h-5" aria-hidden="true" />
              </button>
            </header>

            <div className="ws-form">
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Please confirm permanent deletion of <strong>{user?.email}</strong>. Type <code>DELETE</code> below to proceed.
              </p>

              <label>
                <span>Type DELETE to confirm</span>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder="DELETE"
                />
              </label>

              {user?.has_password && (
                <label>
                  <span>Confirm Account Password</span>
                  <input
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="Your password"
                  />
                </label>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setDeleteModalOpen(false)}
                  className="ws-button"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  disabled={deletingAccount || deleteConfirmText !== 'DELETE'}
                  className="ws-button danger"
                >
                  {deletingAccount ? 'Deleting...' : 'Permanently Delete'}
                </button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<p role="status" className="ws-muted">Loading settings…</p>}>
        <SettingsContent />
      </Suspense>
    </ProtectedRoute>
  );
}
