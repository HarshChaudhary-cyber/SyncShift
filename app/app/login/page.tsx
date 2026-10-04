'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { EyeIcon, EyeSlashIcon, ExclamationTriangleIcon, CheckCircleIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useAuthContext } from '@/context/AuthContext';
import { api, ApiError, PublicInstitution } from '@/lib/api';
import { TurnstileWidget } from '@/components/auth/TurnstileWidget';
import { safeReturnUrl } from '@/lib/session-policy.mjs';

export default function LoginPage() {
  const router = useRouter();
  const { status, user, login, refreshUser, error: sessionError, logout } = useAuthContext();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [selectedInstitutionId, setSelectedInstitutionId] = useState<number | undefined>(undefined);
  const [institutions, setInstitutions] = useState<PublicInstitution[]>([]);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string>('');

  // Password Recovery / Setup Modal State
  const [recoveryOpen, setRecoveryOpen] = useState(false);
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [recoveryToken, setRecoveryToken] = useState('');
  const [recoveryNewPassword, setRecoveryNewPassword] = useState('');
  const [recoveryStep, setRecoveryStep] = useState<'request' | 'reset'>('request');
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [recoveryError, setRecoveryError] = useState<string | null>(null);
  const [recoverySuccess, setRecoverySuccess] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlError = params.get('error');
      if (urlError) {
        setError(urlError);
      }
    }
  }, []);

  // Fetch active institutions for university selector when using enrollment number
  useEffect(() => {
    let active = true;
    api.getPublicInstitutions()
      .then((data) => {
        if (active && Array.isArray(data)) {
          setInstitutions(data);
          if (data.length === 1) {
            setSelectedInstitutionId(data[0].id);
          }
        }
      })
      .catch(() => {
        // Silently fall back if institutions endpoint is not reachable
      });
    return () => {
      active = false;
    };
  }, []);

  // Redirect only after verified authentication
  useEffect(() => {
    if (status === 'authenticated' && user) {
      router.replace(safeReturnUrl(new URLSearchParams(window.location.search).get('returnTo')));
    }
  }, [status, user, router]);

  const isEnrollmentLogin = identifier.trim().length > 0 && !identifier.includes('@');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanId = identifier.trim();
    if (!cleanId) {
      setError('University email or enrollment/roll number is required');
      return;
    }
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);

    try {
      await login(cleanId, password, captchaToken, isEnrollmentLogin ? selectedInstitutionId : undefined);
      router.replace(safeReturnUrl(new URLSearchParams(window.location.search).get('returnTo')));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.code === 'institution_selection_required') {
          setError(err.message || 'Multiple universities found with this enrollment number. Please select your university.');
        } else if (err.status === 401) {
          setError('Invalid login details');
        } else {
          setError(err.message || 'Invalid login details');
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRequestRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryError(null);
    setRecoverySuccess(null);
    if (!recoveryEmail.trim()) {
      setRecoveryError('Please provide your university account email address.');
      return;
    }

    setRecoveryLoading(true);
    try {
      await api.forgotPassword(recoveryEmail.trim());
      // The backend never returns the reset token in the response (security hardening).
      // In production the token is delivered via email; for dev it is in the server log.
      setRecoverySuccess(
        'If an eligible account with that email exists, a password reset link has been sent. ' +
        'Contact your administrator or check server logs (dev) to obtain the token, then paste it below.'
      );
      setRecoveryStep('reset');
    } catch (err: unknown) {
      setRecoveryError(err instanceof Error ? err.message : 'Unable to request password recovery. Please try again.');
    } finally {
      setRecoveryLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryError(null);
    if (!recoveryToken.trim()) {
      setRecoveryError('Reset authorization token is required.');
      return;
    }
    if (recoveryNewPassword.length < 8) {
      setRecoveryError('Password must be at least 8 characters long.');
      return;
    }
    if (!/[A-Z]/.test(recoveryNewPassword) || !/\d/.test(recoveryNewPassword)) {
      setRecoveryError('Password must contain at least one uppercase letter and one number.');
      return;
    }

    setRecoveryLoading(true);
    try {
      await api.resetPassword(recoveryToken.trim(), recoveryNewPassword);
      setRecoverySuccess('Your password has been successfully established! You can now sign in.');
      setTimeout(() => {
        setRecoveryOpen(false);
        setRecoveryStep('request');
        setRecoveryEmail('');
        setRecoveryToken('');
        setRecoveryNewPassword('');
        setRecoverySuccess(null);
      }, 2000);
    } catch (err: unknown) {
      setRecoveryError(err instanceof Error ? err.message : 'Password update failed. The token may be expired or invalid.');
    } finally {
      setRecoveryLoading(false);
    }
  };

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div role="alert" className="space-y-5 max-w-md">
          <h1 className="text-xl">Session verification unavailable</h1>
          <p>{sessionError}</p>
          <button onClick={refreshUser} className="underline mr-6">Retry verification</button>
          <button onClick={logout} className="underline">Return to sign in</button>
        </div>
      </div>
    );
  }

  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Spinner size={32} />
          <p className="text-[var(--text-secondary)] text-sm">Checking your session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col items-center justify-center px-4 py-4 sm:py-8 my-auto overflow-y-auto">
      {/* Ambient background glow */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(99,102,241,0.14) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[420px]">
        {/* Brand wordmark */}
        <div className="flex items-center justify-center gap-2 mb-4 sm:mb-6">
          <span className="text-2xl sm:text-3xl select-none">⚡</span>
          <span className="text-xl sm:text-2xl font-bold text-[var(--text-primary)] tracking-tight">SyncShift</span>
        </div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="px-5 sm:px-6 pt-5 sm:pt-6 pb-2 text-center">
            <h1 className="text-lg sm:text-xl font-semibold text-[var(--text-primary)] tracking-tight">University Sign In</h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Sign in to your university workspace, timetable and academic schedules
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-3.5 sm:space-y-4">
            {/* Identifier input */}
            <div className="space-y-1.5">
              <label htmlFor="identifier" className="block text-xs font-medium text-[var(--text-secondary)]">
                University email or enrollment/roll number
              </label>
              <input
                id="identifier"
                type="text"
                autoComplete="username"
                required
                value={identifier}
                onChange={(e) => {
                  setIdentifier(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="student@university.edu or enrollment number"
                className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3.5 py-2.5 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
              />
            </div>

            {/* University selector shown if enrollment/roll number is detected */}
            {isEnrollmentLogin && institutions.length > 0 && (
              <div className="space-y-1.5 pt-0.5">
                <label htmlFor="institution" className="block text-xs font-medium text-[var(--text-secondary)]">
                  University / Institution
                </label>
                <select
                  id="institution"
                  value={selectedInstitutionId ?? ''}
                  onChange={(e) => setSelectedInstitutionId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-xs sm:text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
                >
                  <option value="">Choose university (or auto-detect)</option>
                  {institutions.map((inst) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name} ({inst.code})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Password input with Heroicons visibility control */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="block text-xs font-medium text-[var(--text-secondary)]">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setRecoveryEmail(identifier.includes('@') ? identifier.trim() : '');
                    setRecoveryError(null);
                    setRecoverySuccess(null);
                    setRecoveryStep('request');
                    setRecoveryOpen(true);
                  }}
                  className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
                >
                  Forgot or set password?
                </button>
              </div>
              <div className="relative w-full">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••"
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg pl-3.5 pr-10 py-2.5 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 transition cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="w-5 h-5" aria-hidden="true" />
                  ) : (
                    <EyeIcon className="w-5 h-5" aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>

            {/* Error message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-start gap-2 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-700/60 rounded-lg px-3.5 py-2.5 break-words"
                >
                  <ExclamationTriangleIcon className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" aria-hidden="true" />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Bot Protection / Turnstile */}
            <TurnstileWidget onVerify={(token) => setCaptchaToken(token)} />

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-colors shadow-md shadow-indigo-950/40 cursor-pointer min-h-[42px]"
            >
              {loading ? (
                <>
                  <Spinner size={16} />
                  <span>Signing in…</span>
                </>
              ) : (
                <span>Sign in</span>
              )}
            </button>
          </form>

          {/* Footer note */}
          <div className="px-5 sm:px-6 pb-4 sm:pb-5 text-center border-t border-[var(--border-color)] pt-3 sm:pt-4">
            <p className="text-xs text-[var(--text-secondary)]">
              Don&apos;t have an account?{' '}
              <Link
                href="/signup"
                className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium cursor-pointer transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>
        </motion.div>

        {/* Back to landing */}
        <p className="mt-3 sm:mt-4 text-center text-xs text-[var(--text-muted)]">
          <Link href="/" className="hover:text-[var(--text-primary)] transition-colors">
            ← Back to home
          </Link>
        </p>
      </div>

      {/* Password Setup & Recovery Modal */}
      {recoveryOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
              <h2 className="text-base font-semibold text-[var(--text-primary)]">
                {recoveryStep === 'request' ? 'Password Setup & Recovery' : 'Create New Password'}
              </h2>
              <button
                type="button"
                onClick={() => setRecoveryOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 rounded-lg"
                aria-label="Close dialog"
              >
                <XMarkIcon className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>

            {recoveryError && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                <ExclamationTriangleIcon className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{recoveryError}</span>
              </div>
            )}

            {recoverySuccess && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                <CheckCircleIcon className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{recoverySuccess}</span>
              </div>
            )}

            {recoveryStep === 'request' ? (
              <form onSubmit={handleRequestRecovery} className="space-y-4">
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  Enter your university email address. If you previously signed in with Google or Microsoft and need to establish a password, this will create your password credentials.
                </p>
                <div>
                  <label htmlFor="recoveryEmail" className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    University Email
                  </label>
                  <input
                    id="recoveryEmail"
                    type="email"
                    required
                    value={recoveryEmail}
                    onChange={(e) => setRecoveryEmail(e.target.value)}
                    placeholder="user@university.edu"
                    className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRecoveryOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={recoveryLoading || !recoveryEmail.trim()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50"
                  >
                    {recoveryLoading ? 'Processing…' : 'Continue'}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div>
                  <label htmlFor="recoveryToken" className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    Reset Token
                  </label>
                  <input
                    id="recoveryToken"
                    type="text"
                    required
                    value={recoveryToken}
                    onChange={(e) => setRecoveryToken(e.target.value)}
                    placeholder="Paste the reset token from your email or server log"
                    className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-xs"
                  />
                  <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
                    The token was sent to your email. Contact your administrator if you didn&apos;t receive it.
                  </span>
                </div>
                <div>
                  <label htmlFor="recoveryNewPassword" className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                    New Password
                  </label>
                  <input
                    id="recoveryNewPassword"
                    type="password"
                    required
                    value={recoveryNewPassword}
                    onChange={(e) => setRecoveryNewPassword(e.target.value)}
                    placeholder="At least 8 chars, 1 uppercase, 1 number"
                    className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-[11px] text-[var(--text-muted)] mt-1 block">
                    Must contain at least 8 characters, one uppercase letter, and one number.
                  </span>
                </div>
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRecoveryStep('request')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={recoveryLoading || !recoveryNewPassword || !recoveryToken.trim()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50"
                  >
                    {recoveryLoading ? 'Saving…' : 'Save New Password'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="animate-spin text-white"
      aria-hidden="true"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}
