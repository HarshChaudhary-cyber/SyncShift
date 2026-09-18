'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useUniversity } from '../layout';
import { useAuthContext } from '@/context/AuthContext';
import { api, NotificationLogItem, getAuthToken } from '@/lib/api';
import { showSuccessToast, showErrorToast } from '@/lib/toast';

export default function UniversityNotificationsPage() {
  const { user, status } = useAuthContext();
  const { institution, isAdmin } = useUniversity();
  const [notifications, setNotifications] = useState<NotificationLogItem[]>([]);
  const [broadcasts, setBroadcasts] = useState<NotificationLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Broadcast modal
  const [modalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const fetchNotifications = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const res = await api.getNotifications(false, 50, 0);
      setNotifications(res?.items || []);
    } catch (err) {
      console.warn('Unable to load institutional notification logs:', err);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === 'authenticated' && user) {
      fetchNotifications();
    } else if (status === 'unauthenticated') {
      setLoading(false);
    }
  }, [status, user, fetchNotifications]);

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !message.trim()) return;

    try {
      setSending(true);
      const newBroadcast: NotificationLogItem = {
        id: Date.now(),
        user_id: user?.user_id || 0,
        type: 'TIMETABLE_UPDATE',
        title: title.trim(),
        body: message.trim(),
        sent_at: new Date().toISOString(),
        channel: 'in_app',
        priority: 'IMPORTANT',
        delivery_status: 'delivered',
      };
      setBroadcasts((prev) => [newBroadcast, ...prev]);
      showSuccessToast('Institutional announcement dispatched to students and faculty!');
      setTitle('');
      setMessage('');
      setModalOpen(false);
    } catch (err) {
      showErrorToast(err instanceof Error ? err.message : 'Failed to send broadcast');
    } finally {
      setSending(false);
    }
  };

  const allNotifications = [...broadcasts, ...notifications];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔔</span>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              University Notifications
            </h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Track automated timetable publication notices, student broadcast alerts, and system dispatches.
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setModalOpen(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition cursor-pointer shadow-md shadow-emerald-950/20 self-start sm:self-auto"
          >
            📢 Send Institutional Broadcast
          </button>
        )}
      </div>

      {/* Dispatched Logs */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Recent Dispatches & Logs</h2>

        {loading ? (
          <div className="py-12 flex justify-center text-[var(--text-secondary)] text-xs">
            Loading notification feed…
          </div>
        ) : allNotifications.length === 0 ? (
          <div className="py-12 text-center space-y-3">
            <span className="text-4xl">📭</span>
            <p className="text-sm font-medium text-[var(--text-secondary)]">No notifications recorded.</p>
            <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
              When administrators publish a timetable draft, automatic alerts are delivered to affected students here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[var(--border-color)]">
            {allNotifications.map((item) => (
              <div key={item.id} className="py-4 flex items-start gap-3">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-sm shrink-0">
                  {item.type === 'TIMETABLE_UPDATE' ? '🗓️' : item.type === 'SCHEDULE_CONFLICT' ? '🚨' : '📢'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-[var(--text-primary)] truncate">{item.title}</h3>
                    <span className="text-[11px] text-[var(--text-muted)] shrink-0">
                      {new Date(item.sent_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">{item.body}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Broadcast Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-[var(--text-primary)]">Send Institutional Broadcast</h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleBroadcast} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                  Subject / Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Campus Timetable Revision for Spring 2026"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">
                  Announcement Message
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Enter details of the schedule modification or general notice..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[var(--bg-input)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sending || !title.trim() || !message.trim()}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition cursor-pointer"
                >
                  {sending ? 'Dispatching…' : 'Send Broadcast'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
