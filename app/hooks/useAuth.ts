'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  api,
  ApiError,
  UserProfile,
  setAuthToken,
  getAuthToken,
  clearAuthToken,
} from '@/lib/api';

export type AuthStatus = 'checking' | 'authenticated' | 'unauthenticated';

export interface UseAuthReturn {
  /** 'checking' while verifying the stored token; then 'authenticated' or 'unauthenticated'. */
  status: AuthStatus;
  user: UserProfile | null;
  /** Call on successful login/register — stores token and sets status = authenticated. */
  login: (email: string, password: string, captcha_token?: string) => Promise<void>;
  /** Like login, but also accepts signup-specific fields with sensible defaults. */
  register: (
    email: string,
    password: string,
    timezone?: string,
    weeklyLimit?: number,
    captcha_token?: string,
  ) => Promise<void>;
  /** Accepts OAuth login/signup response data, saves token, and activates session. */
  loginWithOAuthData: (data: any) => Promise<void>;
  /** Clears localStorage token and resets to unauthenticated. */
  logout: () => void;
  /** Timestamp of the last successful /auth/me or login verification. */
  lastVerified: Date | null;
  /** Re-runs GET /auth/me. Useful to call after an idle wake-up. */
  refreshUser: () => Promise<void>;
  /** Exposed so CalendarContext can trigger a full schedule re-fetch on visibility change. */
  onIdleReturn: React.MutableRefObject<(() => void) | null>;
}

const IDLE_THRESHOLD_MS = 30 * 60 * 1000; // 30 minutes

export function useAuth(): UseAuthReturn {
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [lastVerified, setLastVerified] = useState<Date | null>(null);

  /**
   * Callback ref that CalendarContext (or any consumer) can attach to.
   * useAuth calls this when the user returns after being idle for 30+ min.
   */
  const onIdleReturn = useRef<(() => void) | null>(null);

  // Track when the page was last hidden so we can measure idle time.
  const hiddenAtRef = useRef<number | null>(null);

  /** Verify the stored token by calling GET /auth/me. */
  const verifyToken = useCallback(async (): Promise<boolean> => {
    const token = getAuthToken();
    if (!token) {
      setStatus('unauthenticated');
      return false;
    }
    try {
      const profile = await api.getAuthMe();
      setUser(profile);
      setStatus('authenticated');
      setLastVerified(new Date());
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        clearAuthToken();
        setUser(null);
        setStatus('unauthenticated');
      } else {
        // Network / 5xx — keep status as-is; don't log out on transient errors
        setStatus('authenticated'); // optimistic: we had a token, allow access
      }
      return false;
    }
  }, []);

  /** Public: re-run token verification. */
  const refreshUser = useCallback(async () => {
    await verifyToken();
  }, [verifyToken]);

  // ── On mount: check token ──────────────────────────────────────────────
  useEffect(() => {
    verifyToken();
  }, [verifyToken]);

  // ── Idle-refetch via Page Visibility API ────────────────────────────────
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        hiddenAtRef.current = Date.now();
        return;
      }

      // Page became visible again
      if (hiddenAtRef.current !== null) {
        const idleMs = Date.now() - hiddenAtRef.current;
        hiddenAtRef.current = null;

        if (idleMs >= IDLE_THRESHOLD_MS && status === 'authenticated') {
          // Re-verify token in the background, then trigger schedule refetch
          verifyToken().then((ok) => {
            if (ok && onIdleReturn.current) {
              onIdleReturn.current();
            }
          });
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [status, verifyToken]);

  // ── login ─────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string, captchaToken?: string) => {
    const data = await api.login(email, password, captchaToken);
    setAuthToken(data.token);
    const profile = await api.getAuthMe();
    setUser(profile);
    setStatus('authenticated');
    setLastVerified(new Date());
  }, []);

  // ── register ──────────────────────────────────────────────────────────
  const register = useCallback(
    async (
      email: string,
      password: string,
      timezone = 'Europe/London',
      weeklyLimit = 20.0,
      captchaToken?: string,
    ) => {
      const data = await api.register(email, password, timezone, weeklyLimit, captchaToken);
      setAuthToken(data.token);
      const profile = await api.getAuthMe();
      setUser(profile);
      setStatus('authenticated');
      setLastVerified(new Date());
    },
    [],
  );

  // ── loginWithOAuthData ───────────────────────────────────────────────
  const loginWithOAuthData = useCallback(async (data: any) => {
    if (data?.token) {
      setAuthToken(data.token);
    }
    try {
      const profile = await api.getAuthMe();
      setUser(profile);
    } catch {
      setUser({
        user_id: data.user_id,
        email: data.email,
        timezone: data.timezone || 'Europe/London',
        weekly_work_hour_limit: 20.0,
        display_name: data.display_name,
        avatar_url: data.avatar_url,
      });
    }
    setStatus('authenticated');
    setLastVerified(new Date());
  }, []);

  // ── logout ────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setStatus('unauthenticated');
    setLastVerified(null);
  }, []);

  return {
    status,
    user,
    login,
    register,
    loginWithOAuthData,
    logout,
    lastVerified,
    refreshUser,
    onIdleReturn,
  };
}
