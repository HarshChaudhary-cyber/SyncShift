'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { api, NotificationLogItem } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { isUniversityRole } from '@/components/RoleGuard';

export default function NotificationCenterPage() {
  const { user, status } = useAuthContext();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === 'authenticated' && user && pathname === '/notifications') {
      const isUniv = isUniversityRole(user.institution_role);
      router.replace(isUniv ? '/university/notifications' : '/student/notifications');
    }
  }, [status, user, pathname, router]);

  const [activeTab, setActiveTab] = useState<'unread' | 'all'>('unread');

  const [notifications, setNotifications] = useState<NotificationLogItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchNotifications = async (tab: 'unread' | 'all') => {
    try {
      setLoading(true);
      const res = await api.getNotifications(tab === 'unread', 50, 0);
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchNotifications(activeTab);
  }, [user, activeTab]);

  const handleMarkAsRead = async (id: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      setActionLoading(id);
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
      if (activeTab === 'unread') {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }
    } catch (err) {
      console.error('Failed to mark read:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      setLoading(true);
      await api.markAllNotificationsRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: new Date().toISOString() }))
      );
      setUnreadCount(0);
      if (activeTab === 'unread') {
        setNotifications([]);
      }
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityBadge = (priority?: string) => {
    const p = (priority || 'INFO').toUpperCase();
    if (p === 'URGENT') {
      return (
        <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/15 text-rose-500 border border-rose-500/30">
          ⚠️ URGENT
        </span>
      );
    }
    if (p === 'IMPORTANT') {
      return (
        <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-500 border border-amber-500/30">
          ⚡ IMPORTANT
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
        ℹ️ INFO
      </span>
    );
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'SCHEDULE_CONFLICT':
        return '🚨';
      case 'CLASS_MOVED':
        return '🔄';
      case 'CLASS_ROOM_CHANGED':
        return '🏢';
      case 'CLASS_FACULTY_CHANGED':
        return '👨‍🏫';
      case 'CLASS_ADDED':
        return '➕';
      case 'CLASS_REMOVED':
        return '➖';
      case 'TIMETABLE_UPDATE':
        return '📅';
      case 'shift':
        return '💼';
      case 'study':
        return '📖';
      case 'deadline':
        return '⏳';
      default:
        return '🔔';
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header Breadcrumbs & Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border-color)] pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-1">
              <Link
                href={isUniversityRole(user?.institution_role) ? "/university/dashboard" : "/student/dashboard"}
                className="hover:text-indigo-400 transition"
              >
                Home
              </Link>
              <span>/</span>
              <span className="text-[var(--text-secondary)] font-medium">Notification Center</span>
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight flex items-center gap-2">
                <span>Notifications</span>
                {unreadCount > 0 && (
                  <span className="px-2.5 py-0.5 rounded-full bg-indigo-600 text-white text-xs font-bold shadow-sm">
                    {unreadCount} unread
                  </span>
                )}
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-[var(--text-secondary)] mt-1">
              Stay updated on official timetable changes, room moves, and work schedule conflicts.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-3">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={loading}
                className="px-3 py-1.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] text-xs font-semibold text-[var(--text-primary)] transition cursor-pointer flex items-center gap-1.5 shadow-xs"
              >
                <span>✓</span>
                <span>Mark all as read</span>
              </button>
            )}
            <Link
              href="/settings?tab=notifications"
              className="px-3 py-1.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:bg-[var(--bg-secondary)] text-xs font-medium text-[var(--text-secondary)] hover:text-indigo-400 transition flex items-center gap-1.5 shadow-xs"
            >
              <span>⚙️</span>
              <span>Preferences</span>
            </Link>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="flex items-center gap-2 border-b border-[var(--border-color)]">
          <button
            onClick={() => setActiveTab('unread')}
            className={`pb-3 px-4 text-sm font-semibold transition border-b-2 cursor-pointer flex items-center gap-2 ${
              activeTab === 'unread'
                ? 'border-indigo-500 text-indigo-500'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
          >
            <span>Unread</span>
            {unreadCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-500 text-xs font-bold">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-3 px-4 text-sm font-semibold transition border-b-2 cursor-pointer ${
              activeTab === 'all'
                ? 'border-indigo-500 text-indigo-500'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
          >
            All Notifications
          </button>
        </div>

        {/* Notifications List */}
        <div className="space-y-3">
          {loading ? (
            <div className="p-12 text-center text-sm text-[var(--text-muted)] bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] animate-pulse">
              Loading your notifications...
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] shadow-xs">
              <span className="block text-4xl mb-3">✨</span>
              <h3 className="text-base font-bold text-[var(--text-primary)] mb-1">
                {activeTab === 'unread' ? "You're all caught up!" : 'No notifications yet'}
              </h3>
              <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto mb-4">
                {activeTab === 'unread'
                  ? 'All timetable updates and conflict alerts have been acknowledged.'
                  : "When your university updates your timetable, you'll see exact details here."}
              </p>
              <Link
                href="/student/calendar"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-sm transition"
              >
                <span>📅 View My Schedule</span>
              </Link>
            </div>
          ) : (
            notifications.map((notif) => {
              const isUnread = !notif.read_at;
              const hasMetadata = Boolean(notif.metadata_json);
              let metaObj: any = null;
              if (hasMetadata) {
                try {
                  metaObj = JSON.parse(notif.metadata_json!);
                } catch {
                  metaObj = null;
                }
              }

              const isExpanded = expandedId === notif.id;

              return (
                <div
                  key={notif.id}
                  className={`p-4 sm:p-5 rounded-2xl border transition shadow-xs ${
                    isUnread
                      ? 'bg-[var(--bg-card)] border-indigo-500/40 ring-1 ring-indigo-500/10'
                      : 'bg-[var(--bg-card)] border-[var(--border-color)] opacity-85 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1">
                      {/* Icon */}
                      <div className="w-10 h-10 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-center text-lg shrink-0">
                        {getTypeIcon(notif.type)}
                      </div>

                      {/* Content */}
                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-bold text-[var(--text-primary)]">
                            {notif.title}
                          </span>
                          {getPriorityBadge(notif.priority)}
                          {isUnread && (
                            <span className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" title="Unread" />
                          )}
                        </div>

                        <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
                          {notif.body}
                        </p>

                        {/* Metadata Details Preview (Before/After) if available */}
                        {metaObj && metaObj.changes && metaObj.changes.length > 0 && (
                          <div className="pt-2">
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : notif.id)}
                              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 cursor-pointer"
                            >
                              <span>{isExpanded ? 'Hide' : 'View'} change details ({metaObj.total_changes || metaObj.changes.length})</span>
                              <span>{isExpanded ? '▲' : '▼'}</span>
                            </button>

                            {isExpanded && (
                              <div className="mt-2.5 p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2 text-xs">
                                {metaObj.changes.map((ch: any, idx: number) => (
                                  <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border-color)] last:border-b-0 pb-2 last:pb-0">
                                    <div>
                                      <span className="font-bold text-[var(--text-primary)]">{ch.course_name}</span>
                                      <span className="text-[var(--text-muted)] ml-1.5 font-mono text-[11px]">({ch.section_code})</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-[11px]">
                                      {ch.before_day_name && (
                                        <span className="text-[var(--text-muted)] line-through">
                                          {ch.before_day_name} {ch.before_start}–{ch.before_end} ({ch.before_room})
                                        </span>
                                      )}
                                      <span className="text-indigo-400 font-bold">→</span>
                                      <span className="text-emerald-400 font-semibold">
                                        {ch.after_day_name} {ch.after_start}–{ch.after_end} ({ch.after_room})
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="pt-3 flex flex-wrap items-center gap-3">
                          {notif.action_url && (
                            <Link
                              href={notif.action_url}
                              onClick={() => {
                                if (isUnread) handleMarkAsRead(notif.id);
                              }}
                              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition inline-flex items-center gap-1.5 ${
                                notif.priority === 'URGENT'
                                  ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-xs'
                                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs'
                              }`}
                            >
                              <span>{notif.priority === 'URGENT' ? '⚠️ Review Conflict' : '📅 View My Schedule'}</span>
                              <span>→</span>
                            </Link>
                          )}

                          {isUnread && (
                            <button
                              onClick={(e) => handleMarkAsRead(notif.id, e)}
                              disabled={actionLoading === notif.id}
                              className="px-3 py-1.5 rounded-xl border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer"
                            >
                              {actionLoading === notif.id ? 'Marking...' : 'Mark as read'}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Time & Delivery details */}
                    <div className="text-right shrink-0 text-[11px] text-[var(--text-muted)] flex flex-col items-end gap-1">
                      <span>
                        {notif.sent_at
                          ? new Date(notif.sent_at).toLocaleDateString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : ''}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] text-[10px] uppercase font-mono">
                        {notif.channel}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
