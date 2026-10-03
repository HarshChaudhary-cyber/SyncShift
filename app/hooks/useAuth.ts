'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { api, UserProfile, ClassSummary, setAuthToken, getAuthToken, clearAuthToken, AUTH_TOKEN_KEY } from '@/lib/api';
import { verifySession } from '@/lib/session-policy.mjs';
import { applyReducedMotion, resetReducedMotion } from '@/lib/preferences';

export type AuthStatus = 'checking' | 'authenticated' | 'unauthenticated' | 'error';
export interface UseAuthReturn {
  status: AuthStatus;
  user: UserProfile | null;
  memberships: ClassSummary[];
  error: string | null;
  login: (email: string, password: string, captcha?: string) => Promise<void>;
  register: (email: string, password: string, timezone?: string, limit?: number, captcha?: string) => Promise<void>;
  loginWithOAuthData: (data: {token?: string}) => Promise<void>;
  logout: () => void;
  lastVerified: Date | null;
  refreshUser: () => Promise<void>;
  onIdleReturn: React.MutableRefObject<(() => void) | null>;
}

export function useAuth(): UseAuthReturn {
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [memberships, setMemberships] = useState<ClassSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastVerified, setLastVerified] = useState<Date | null>(null);
  const previous = useRef<{user: UserProfile | null; memberships: ClassSummary[]}>({user: null, memberships: []});
  const generation = useRef(0);
  const onIdleReturn = useRef<(() => void) | null>(null);
  const logout = useCallback(() => {
    generation.current++;
    clearAuthToken(); previous.current = {user: null, memberships: []};
    resetReducedMotion();
    setUser(null); setMemberships([]); setError(null); setLastVerified(null); setStatus('unauthenticated');
  }, []);
  const verifyToken = useCallback(async () => {
    const token = getAuthToken();
    if (!token) { logout(); return false; }
    const requestId = ++generation.current;
    const result = await verifySession(api.getAuthMe, api.getClasses, previous.current);
    if (requestId !== generation.current || getAuthToken() !== token) return false;
    if (result.status === 'unauthenticated') { logout(); return false; }
    setStatus(result.status); setUser(result.user); setMemberships(result.memberships); setError(result.error);
    applyReducedMotion(result.user?.reduced_motion);
    previous.current = {user: result.user, memberships: result.memberships};
    if (result.verified) setLastVerified(new Date());
    return result.verified;
  }, [logout]);
  const establish = useCallback(async (data: {token?: string}) => {
    if (!data.token) throw new Error('No authentication token received.');
    generation.current++; previous.current = {user: null, memberships: []};
    setUser(null); setMemberships([]); setStatus('checking'); setError(null);
    setAuthToken(data.token);
    if (!(await verifyToken())) throw new Error('Sign-in could not be verified. Please retry session verification.');
  }, [verifyToken]);
  useEffect(() => {
    void verifyToken();
    const invalid = () => logout();
    const refresh = () => { if (document.visibilityState === 'visible') void verifyToken().then(ok => { if (ok) onIdleReturn.current?.(); }); };
    const storage = (event: StorageEvent) => { if (event.key && ![AUTH_TOKEN_KEY, 'token'].includes(event.key)) return; previous.current = {user: null, memberships: []}; setStatus('checking'); void verifyToken(); };
    window.addEventListener('syncshift:unauthorized', invalid);
    window.addEventListener('storage', storage);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      generation.current++;
      window.removeEventListener('syncshift:unauthorized', invalid);
      window.removeEventListener('storage', storage);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [verifyToken, logout]);
  const login = useCallback(async (email: string, password: string, captcha?: string) => establish(await api.login(email, password, captcha)), [establish]);
  const register = useCallback(async (email: string, password: string, timezone = 'Europe/London', limit = 20, captcha?: string) => establish(await api.register(email, password, timezone, limit, captcha)), [establish]);
  const refreshUser = useCallback(async () => { await verifyToken(); }, [verifyToken]);
  return {status, user, memberships, error, login, register, loginWithOAuthData: establish, logout, lastVerified, refreshUser, onIdleReturn};
}
