'use client';

import { UserProfile } from './api';

export type TimeFormat = '12h' | '24h';
export type WeekStartDay = 'monday' | 'sunday';
export type ReducedMotionPref = 'system' | 'reduced' | 'normal';
export type CalendarDefaultView = '7day' | '5day';

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
  default_calendar_view: '7day',
  reduced_motion: 'system',
  planning_hours_start: 9,
  planning_hours_end: 18,
  preferred_session_duration: 45,
  preferred_break_duration: 15,
};

/**
 * Safely normalizes previously saved or unknown calendar views to supported values.
 */
export function normalizeCalendarView(view?: string | null): CalendarDefaultView {
  if (view === '5day' || view === 'workweek') return '5day';
  return '7day';
}

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
 * Evaluates whether reduced motion should be active given the explicit preference:
 * - 'reduced' -> true
 * - 'normal'  -> false
 * - 'system'  -> OS prefers-reduced-motion
 */
export function isReducedMotionActive(
  pref?: ReducedMotionPref | string | null,
  osPrefersReduced?: boolean
): boolean {
  if (pref === 'reduced') return true;
  if (pref === 'normal') return false;
  if (typeof osPrefersReduced === 'boolean') return osPrefersReduced;
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  return false;
}

let activeMediaQuery: MediaQueryList | null = null;
let activeMediaListener: ((e: MediaQueryListEvent) => void) | null = null;

function cleanupOsListener() {
  if (activeMediaQuery && activeMediaListener) {
    activeMediaQuery.removeEventListener('change', activeMediaListener);
    activeMediaQuery = null;
    activeMediaListener = null;
  }
}

/**
 * Apply reduced-motion preference centrally to document root and react to OS changes when 'system' is selected.
 */
export function applyReducedMotion(mode?: ReducedMotionPref | string | null): void {
  if (typeof document === 'undefined') return;
  cleanupOsListener();

  const root = document.documentElement;
  const pref: ReducedMotionPref = mode === 'reduced' ? 'reduced' : mode === 'normal' ? 'normal' : 'system';

  const update = (active: boolean) => {
    root.setAttribute('data-reduced-motion-pref', pref);
    root.setAttribute('data-reduced-motion', active ? 'reduced' : 'normal');
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('syncshift:reduced-motion-change', {
          detail: { pref, active },
        })
      );
    }
  };

  if (pref === 'reduced') {
    update(true);
  } else if (pref === 'normal') {
    update(false);
  } else {
    // 'system': resolve via OS matchMedia and react to OS preference changes
    if (typeof window !== 'undefined' && window.matchMedia) {
      activeMediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      update(activeMediaQuery.matches);

      activeMediaListener = (e: MediaQueryListEvent) => {
        update(e.matches);
      };
      activeMediaQuery.addEventListener('change', activeMediaListener);
    } else {
      update(false);
    }
  }
}

/**
 * Resets reduced-motion preference attributes and listeners on logout.
 */
export function resetReducedMotion(): void {
  if (typeof document === 'undefined') return;
  cleanupOsListener();
  const root = document.documentElement;
  root.removeAttribute('data-reduced-motion-pref');
  root.removeAttribute('data-reduced-motion');
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('syncshift:reduced-motion-change', {
        detail: { pref: 'system', active: false },
      })
    );
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
    default_calendar_view: normalizeCalendarView(user.default_calendar_view),
    reduced_motion: (user.reduced_motion as ReducedMotionPref) || 'system',
    planning_hours_start: typeof user.planning_hours_start === 'number' ? user.planning_hours_start : 9,
    planning_hours_end: typeof user.planning_hours_end === 'number' ? user.planning_hours_end : 18,
    preferred_session_duration: typeof user.preferred_session_duration === 'number' ? user.preferred_session_duration : 45,
    preferred_break_duration: typeof user.preferred_break_duration === 'number' ? user.preferred_break_duration : 15,
  };
}
