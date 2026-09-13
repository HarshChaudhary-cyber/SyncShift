'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuthContext } from '@/context/AuthContext';
import { api, NotificationPrefs } from '@/lib/api';
import { getBrowserAndOs, urlBase64ToUint8Array } from '@/lib/notificationHelpers';
import TimePicker from '@/components/ui/TimePicker';
import CustomSelect from '@/components/ui/CustomSelect';

const REMINDER_OPTIONS = [
  { value: 0, label: '0 min (At start)' },
  { value: 15, label: '15 minutes before' },
  { value: 30, label: '30 minutes before' },
  { value: 60, label: '60 minutes (1 hour) before' },
  { value: 120, label: '120 minutes (2 hours) before' },
];

export default function NotificationSettingsPage() {
  const { user } = useAuthContext();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Prefs state
  const [pushEnabled, setPushEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [classReminderMin, setClassReminderMin] = useState(30);
  const [shiftReminderMin, setShiftReminderMin] = useState(60);
  const [studyReminderMin, setStudyReminderMin] = useState(15);
  const [deadlineReminder, setDeadlineReminder] = useState(true);
  const [conflictAlerts, setConflictAlerts] = useState(true);

  // Quiet hours
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState('08:00');

  // Push subscription & permission state
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [browserInfo, setBrowserInfo] = useState('Browser');
  const [isSubscribed, setIsSubscribed] = useState(false);

  // Test push status
  const [testStatus, setTestStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState<string | null>(null);

  // Detect permission and browser on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setBrowserInfo(getBrowserAndOs());
      if ('Notification' in window) {
        setPermission(Notification.permission);
      }
      checkSubscription();
    }
  }, []);

  async function checkSubscription() {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.getRegistration('/sw.js');
      if (reg) {
        const sub = await reg.pushManager.getSubscription();
        setIsSubscribed(!!sub);
      }
    } catch {
      setIsSubscribed(false);
    }
  }

  // Fetch preferences
  useEffect(() => {
    async function loadPrefs() {
      try {
        setLoading(true);
        const prefs = await api.getNotificationPrefs();
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
          setQuietHoursStart('22:00');
          setQuietHoursEnd('08:00');
        }
      } catch (err: any) {
        setSaveError(err.message || 'Failed to load preferences');
      } finally {
        setLoading(false);
      }
    }
    loadPrefs();
  }, []);

  // Subscribe browser to push
  async function handleEnablePush() {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

    try {
      let perm = Notification.permission;
      if (perm === 'default') {
        perm = await Notification.requestPermission();
        setPermission(perm);
      }

      if (perm === 'granted') {
        const reg = await navigator.serviceWorker.register('/sw.js');
        await navigator.serviceWorker.ready;

        const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
        if (!vapidPublicKey) {
          throw new Error('VAPID public key not configured.');
        }

        let sub = await reg.pushManager.getSubscription();
        if (!sub) {
          sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
          });
        }

        if (sub) {
          const subJson = sub.toJSON();
          if (subJson.endpoint && subJson.keys?.p256dh && subJson.keys?.auth) {
            await api.subscribePush({
              endpoint: subJson.endpoint,
              expirationTime: subJson.expirationTime,
              keys: {
                p256dh: subJson.keys.p256dh,
                auth: subJson.keys.auth,
              },
            });
            setIsSubscribed(true);
          }
        }
      }
    } catch (err: any) {
      console.error('Failed to enable push:', err);
    }
  }

  // Toggle push
  async function handleTogglePush(enabled: boolean) {
    setPushEnabled(enabled);
    if (enabled && permission !== 'granted') {
      await handleEnablePush();
    }
    try {
      await api.updateNotificationPrefs({ push_enabled: enabled });
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update push preference');
    }
  }

  // Toggle email
  async function handleToggleEmail(enabled: boolean) {
    setEmailEnabled(enabled);
    try {
      await api.updateNotificationPrefs({ email_enabled: enabled });
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update email preference');
    }
  }

  // Send test notification
  async function handleSendTest() {
    setTestStatus('sending');
    setTestMessage(null);

    // If permission not granted or no sub, try subscribing first
    if (permission !== 'granted' || !isSubscribed) {
      await handleEnablePush();
    }

    try {
      const res = await api.sendTestNotification();
      setTestStatus('success');
      setTestMessage(res.message || 'Notifications are working 🎉');
    } catch (err: any) {
      setTestStatus('error');
      setTestMessage(err.message || 'No push subscription found. Allow notifications in your browser first.');
    }
  }

  // Save all reminder minutes & quiet hours
  async function handleSavePrefs() {
    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    try {
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

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col">
        <Navbar />

        <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8">
          {/* Header */}
          <div className="mb-8">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:text-indigo-400 transition mb-3"
            >
              <span>←</span>
              <span>Back to Dashboard</span>
            </Link>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h1 className="text-2xl sm:text-3xl font-black text-[var(--text-primary)] tracking-tight flex items-center gap-2.5">
                  <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 text-xl border border-indigo-500/20">
                    🔔
                  </span>
                  <span>Notification Settings</span>
                </h1>
                <p className="text-[var(--text-secondary)] text-sm mt-1">
                  Choose how and when SyncShift alerts you for classes, shifts, study blocks, and deadlines.
                </p>
              </div>

              {saveSuccess && (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold animate-fade-in">
                  <span>✓</span>
                  <span>Settings saved</span>
                </div>
              )}
            </div>
          </div>

          {saveError && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between">
              <span>{saveError}</span>
              <button onClick={() => setSaveError(null)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
                ✕
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-24">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 1. Push Notifications Card */}
              <section className="p-5 sm:p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xl backdrop-blur-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[var(--border-color)]">
                  <div>
                    <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                      <span>📲</span>
                      <span>Browser Push Notifications</span>
                    </h2>
                    <p className="text-[var(--text-secondary)] text-xs mt-0.5">
                      Get real-time popups even when SyncShift is running in a background tab.
                    </p>
                  </div>

                  <label className="relative inline-flex items-center cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={pushEnabled}
                      onChange={(e) => handleTogglePush(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                {/* Status Line */}
                <div className="mt-4 py-3 px-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    {permission === 'denied' ? (
                      <span className="text-red-400 font-medium">
                        ❌ Blocked — click the 🔒 icon in your browser address bar to allow notifications
                      </span>
                    ) : permission === 'granted' ? (
                      <span className="text-emerald-400 font-medium">
                        ✅ Connected via {browserInfo}
                      </span>
                    ) : (
                      <span className="text-amber-400 font-medium">
                        ⚠️ Notifications permission pending in {browserInfo}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={handleSendTest}
                    disabled={testStatus === 'sending'}
                    className="self-start sm:self-auto px-3.5 py-1.5 rounded-lg bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] text-[var(--text-primary)] text-xs font-semibold transition border border-[var(--border-color)] active:scale-95 disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                  >
                    <span>{testStatus === 'sending' ? 'Sending...' : '🚀 Send test notification'}</span>
                  </button>
                </div>

                {/* Inline Test Result Banner */}
                {testMessage && (
                  <div
                    className={`mt-3 p-3 rounded-xl text-xs flex items-center gap-2 ${
                      testStatus === 'success'
                        ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                        : 'bg-red-500/10 border border-red-500/30 text-red-300'
                    }`}
                  >
                    <span>{testStatus === 'success' ? '🎉' : '⚠️'}</span>
                    <span>{testMessage}</span>
                  </div>
                )}
              </section>

              {/* 2. Email Reminders Card */}
              <section className="p-5 sm:p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xl backdrop-blur-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                      <span>📧</span>
                      <span>Email Reminders</span>
                    </h2>
                    <p className="text-[var(--text-secondary)] text-xs mt-0.5">
                      Receive schedule reminders in your inbox. Sent to{' '}
                      <span className="text-indigo-400 font-medium">{user?.email}</span>.
                    </p>
                  </div>

                  <label className="relative inline-flex items-center cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={emailEnabled}
                      onChange={(e) => handleToggleEmail(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-neutral-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
              </section>

              {/* 3. Remind Me Before Card */}
              <section className="p-5 sm:p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xl backdrop-blur-sm space-y-5">
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <span>⏰</span>
                    <span>Remind Me Before</span>
                  </h2>
                  <p className="text-[var(--text-secondary)] text-xs mt-0.5">
                    Customize lead times for classes, shifts, and study sessions.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Class */}
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-blue-400 text-sm">🎓</span>
                      <label className="text-xs font-bold text-[var(--text-primary)]">Class</label>
                    </div>
                    <CustomSelect
                      options={REMINDER_OPTIONS}
                      value={classReminderMin}
                      onChange={(v) => setClassReminderMin(Number(v))}
                      size="sm"
                    />
                  </div>

                  {/* Work Shift */}
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-amber-400 text-sm">💼</span>
                      <label className="text-xs font-bold text-[var(--text-primary)]">Work Shift</label>
                    </div>
                    <CustomSelect
                      options={REMINDER_OPTIONS}
                      value={shiftReminderMin}
                      onChange={(v) => setShiftReminderMin(Number(v))}
                      size="sm"
                    />
                  </div>

                  {/* Study Block */}
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-emerald-400 text-sm">📖</span>
                      <label className="text-xs font-bold text-[var(--text-primary)]">Study Block</label>
                    </div>
                    <CustomSelect
                      options={REMINDER_OPTIONS}
                      value={studyReminderMin}
                      onChange={(v) => setStudyReminderMin(Number(v))}
                      size="sm"
                    />
                  </div>
                </div>

                {/* Checkboxes */}
                <div className="pt-3 border-t border-[var(--border-color)] space-y-3">
                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={deadlineReminder}
                      onChange={(e) => setDeadlineReminder(e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded border-[var(--border-color)] text-indigo-600 bg-[var(--bg-input)] focus:ring-indigo-500"
                    />
                    <div>
                      <span className="text-xs font-medium text-[var(--text-primary)]">
                        Remind me 1 day before assignment deadlines
                      </span>
                      <p className="text-[11px] text-[var(--text-muted)]">
                        Dispatched daily at 08:00 in your local timezone for upcoming study tasks.
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start gap-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={conflictAlerts}
                      onChange={(e) => setConflictAlerts(e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded border-[var(--border-color)] text-indigo-600 bg-[var(--bg-input)] focus:ring-indigo-500"
                    />
                    <div>
                      <span className="text-xs font-medium text-[var(--text-primary)]">
                        Alert me immediately when a new schedule conflict appears
                      </span>
                      <p className="text-[11px] text-[var(--text-muted)]">
                        Receive real-time push alerts whenever an enrolled shift overlaps with a class.
                      </p>
                    </div>
                  </label>
                </div>
              </section>

              {/* 4. Quiet Hours Card */}
              <section className="p-5 sm:p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xl backdrop-blur-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                      <span>🌙</span>
                      <span>Quiet Hours (Optional)</span>
                    </h2>
                    <p className="text-[var(--text-secondary)] text-xs mt-0.5">
                      Pause all notification delivery during your sleep or focus window.
                    </p>
                  </div>

                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={quietHoursEnabled}
                      onChange={(e) => setQuietHoursEnabled(e.target.checked)}
                      className="w-4 h-4 rounded border-[var(--border-color)] text-indigo-600 bg-[var(--bg-input)] focus:ring-indigo-500"
                    />
                    <span className="text-xs font-medium text-[var(--text-secondary)]">Enable quiet hours</span>
                  </label>
                </div>

                {quietHoursEnabled && (
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-3">
                    <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 text-xs text-[var(--text-secondary)]">
                      <span className="shrink-0">No notifications from</span>
                      <div className="w-full sm:w-36">
                        <TimePicker
                          value={quietHoursStart}
                          onChange={setQuietHoursStart}
                        />
                      </div>
                      <span className="shrink-0">to</span>
                      <div className="w-full sm:w-36">
                        <TimePicker
                          value={quietHoursEnd}
                          onChange={setQuietHoursEnd}
                        />
                      </div>
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Quiet hours apply to everything, including conflict alerts.
                    </p>
                  </div>
                )}
              </section>

              {/* Save Button Bar */}
              <div className="flex items-center justify-end gap-3 pt-4">
                <button
                  onClick={handleSavePrefs}
                  disabled={saving}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-950/50 transition active:scale-95 disabled:opacity-50 cursor-pointer flex items-center gap-2"
                >
                  <span>{saving ? 'Saving...' : 'Save Preferences'}</span>
                  {saveSuccess && <span>✓</span>}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}
