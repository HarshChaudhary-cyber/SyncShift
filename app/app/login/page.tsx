'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthContext } from '@/context/AuthContext';
import { ApiError } from '@/lib/api';
import { OAuthButtons, OAuthDivider } from '@/components/auth/OAuthButtons';
import { TurnstileWidget } from '@/components/auth/TurnstileWidget';
import { getPortalRedirect } from '@/components/RoleGuard';

export default function LoginPage() {
  const router = useRouter();
  const { status, user, login } = useAuthContext();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string>('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlError = params.get('error');
      if (urlError) {
        setError(urlError);
      }
    }
  }, []);

  // If already authenticated, redirect to the correct portal
  useEffect(() => {
    if (status === 'authenticated' && user) {
      router.replace(getPortalRedirect(user.institution_role));
    }
  }, [status, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (!email.trim()) {
      setError('Email address is required');
      return;
    }
    if (!password) {
      setError('Password is required');
      return;
    }

    setLoading(true);

    try {
      await login(email.trim(), password, captchaToken);
      // After login, useAuth will have updated user profile — redirect based on role
      // We need to get the profile after login to know the role
      const { api } = await import('@/lib/api');
      const profile = await api.getAuthMe();
      router.replace(getPortalRedirect(profile.institution_role));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError('Invalid email or password');
        } else {
          setError(err.message || 'Invalid email or password');
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

  // Show spinner while checking session
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

      <div className="relative z-10 w-full max-w-[400px]">
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
            <h1 className="text-lg sm:text-xl font-semibold text-[var(--text-primary)] tracking-tight">Welcome back</h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Sign in to manage your student timetable and work shifts
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-3.5 sm:space-y-4">
            {/* Email input */}
            <div className="space-y-1.5">
              <label htmlFor="email" className="block text-xs font-medium text-[var(--text-secondary)]">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="student@university.edu"
                className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3.5 py-2.5 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
              />
            </div>

            {/* Password input */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="block text-xs font-medium text-[var(--text-secondary)]">
                  Password
                </label>
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
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 text-xs transition cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
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
                  <span className="shrink-0 mt-0.5">⚠️</span>
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

          {/* Divider & OAuth buttons */}
          <div className="px-5 sm:px-6 pb-5 pt-0">
            <OAuthDivider text="OR" />
            <OAuthButtons captchaToken={captchaToken} />
          </div>

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
