'use client';

import { UserProfile } from './api';

export type TimeFormat = '12h' | '24h';
export type WeekStartDay = 'monday' | 'sunday';
export type ReducedMotionPref = 'system' | 'reduced' | 'normal';
export type CalendarDefaultView = 'week' | 'day' | 'month' | '7day' | '5day';

export interface ExtendedPreferences {
  week_starts_on: WeekStartDay;
  time_format: TimeFormat;
  default_calendar_view: CalendarDefaultView;
  reduced_motion: ReducedMotionPref;
  planning_hours_start: number;
  planning_hours_end: number;
  preferred_session_duration: number;
  preferred_break_duration: number;
}

export const DEFAULT_PREFERENCES: ExtendedPreferences = {
  week_starts_on: 'monday',
  time_format: '12h',
  default_calendar_view: 'week',
  reduced_motion: 'system',
  planning_hours_start: 9,
  planning_hours_end: 18,
  preferred_session_duration: 45,
  preferred_break_duration: 15,
};

/**
 * Format a HH:MM or HH:MM:SS string according to 12h or 24h format.
 * Returns empty string if input is blank or invalid.
 */
export function formatTimeDisplay(timeStr?: string | null, format: TimeFormat = '12h'): string {
  if (!timeStr) return '';
  const clean = timeStr.trim().slice(0, 5);
  if (!clean.includes(':')) return clean;

  if (format === '24h') {
    return clean;
  }

  const [hStr, mStr] = clean.split(':');
  const h = parseInt(hStr, 10);
  if (isNaN(h)) return clean;

  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${mStr} ${ampm}`;
}

/**
 * Format a time range "09:00 - 10:30" according to 12h or 24h format.
 */
export function formatTimeRangeDisplay(startTime?: string | null, endTime?: string | null, format: TimeFormat = '12h'): string {
  if (!startTime && !endTime) return '';
  if (startTime && !endTime) return formatTimeDisplay(startTime, format);
  if (!startTime && endTime) return formatTimeDisplay(endTime, format);
  return `${formatTimeDisplay(startTime, format)} – ${formatTimeDisplay(endTime, format)}`;
}

/**
 * Generate a user-scoped localStorage key to prevent preferences leaking between accounts.
 */
export function getUserPrefKey(userId: number | string | undefined, key: string): string {
  const uid = userId ? String(userId) : 'guest';
  return `syncshift_user_${uid}_${key}`;
}

/**
 * Apply reduced-motion preference to document root.
 */
export function applyReducedMotion(mode: ReducedMotionPref): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (mode === 'reduced') {
    root.setAttribute('data-reduced-motion', 'reduced');
  } else if (mode === 'normal') {
    root.setAttribute('data-reduced-motion', 'normal');
  } else {
    root.removeAttribute('data-reduced-motion');
  }
}

/**
 * Extract full preferences safely from a user profile with fallback to defaults.
 */
export function getPreferencesFromUser(user?: UserProfile | null): ExtendedPreferences {
  if (!user) return { ...DEFAULT_PREFERENCES };

  return {
    week_starts_on: user.week_starts_on === 'sunday' ? 'sunday' : 'monday',
    time_format: user.time_format === '24h' ? '24h' : '12h',
    default_calendar_view: (user.default_calendar_view as CalendarDefaultView) || 'week',
    reduced_motion: (user.reduced_motion as ReducedMotionPref) || 'system',
    planning_hours_start: typeof user.planning_hours_start === 'number' ? user.planning_hours_start : 9,
    planning_hours_end: typeof user.planning_hours_end === 'number' ? user.planning_hours_end : 18,
    preferred_session_duration: typeof user.preferred_session_duration === 'number' ? user.preferred_session_duration : 45,
    preferred_break_duration: typeof user.preferred_break_duration === 'number' ? user.preferred_break_duration : 15,
  };
}
