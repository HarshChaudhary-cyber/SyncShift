'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthContext } from '@/context/AuthContext';
import { ApiError } from '@/lib/api';
import { OAuthButtons, OAuthDivider } from '@/components/auth/OAuthButtons';
import { TurnstileWidget } from '@/components/auth/TurnstileWidget';
import { getPortalRedirect } from '@/components/RoleGuard';
import CustomSelect from '@/components/ui/CustomSelect';
import { TIMEZONE_OPTIONS } from '@/lib/timezones';

const COMMON_TIMEZONES = [
  { value: 'Europe/London', label: 'Europe/London (GMT/BST)' },
  { value: 'America/New_York', label: 'America/New_York (Eastern Time)' },
  { value: 'America/Chicago', label: 'America/Chicago (Central Time)' },
  { value: 'America/Denver', label: 'America/Denver (Mountain Time)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (Pacific Time)' },
  { value: 'America/Toronto', label: 'America/Toronto (Eastern Time)' },
  { value: 'America/Vancouver', label: 'America/Vancouver (Pacific Time)' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin (CET/CEST)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (CET/CEST)' },
  { value: 'Europe/Dublin', label: 'Europe/Dublin (IST/GMT)' },
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (IST +5:30)' },
  { value: 'Asia/Singapore', label: 'Asia/Singapore (SGT +8:00)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (JST +9:00)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (GST +4:00)' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney (AEST/AEDT)' },
  { value: 'Australia/Melbourne', label: 'Australia/Melbourne (AEST/AEDT)' },
  { value: 'Pacific/Auckland', label: 'Pacific/Auckland (NZST/NZDT)' },
];

export default function SignupPage() {
  const router = useRouter();
  const { status, user, register: authRegister } = useAuthContext();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [timezone, setTimezone] = useState('Europe/London');
  const [tzSearch, setTzSearch] = useState('');
  const [weeklyLimit, setWeeklyLimit] = useState(20);
  const [agreeTerms, setAgreeTerms] = useState(false);

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

  // Real-time password strength evaluation
  const passwordCriteria = useMemo(() => {
    return {
      hasMinLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasNumber: /\d/.test(password),
    };
  }, [password]);

  const passwordScore = useMemo(() => {
    let score = 0;
    if (passwordCriteria.hasMinLength) score++;
    if (passwordCriteria.hasUppercase) score++;
    if (passwordCriteria.hasNumber) score++;
    return score;
  }, [passwordCriteria]);

  const passwordsMatch = useMemo(() => {
    if (!confirmPassword) return null;
    return password === confirmPassword;
  }, [password, confirmPassword]);

  const filteredTimezones = useMemo(() => {
    if (!tzSearch.trim()) return COMMON_TIMEZONES;
    const q = tzSearch.toLowerCase();
    return COMMON_TIMEZONES.filter(
      (tz) => tz.label.toLowerCase().includes(q) || tz.value.toLowerCase().includes(q)
    );
  }, [tzSearch]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setError('Please enter a valid email address');
      return;
    }

    if (passwordScore < 3) {
      setError('Password must be at least 8 characters long, contain at least 1 uppercase letter and 1 number');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!timezone) {
      setError('Please select a valid timezone');
      return;
    }

    if (!weeklyLimit || weeklyLimit <= 0) {
      setError('Weekly work hour limit must be greater than 0');
      return;
    }

    if (!agreeTerms) {
      setError('You must agree to the terms to create an account');
      return;
    }

    setLoading(true);

    try {
      await authRegister(email.trim(), password, timezone, weeklyLimit, captchaToken);
      router.replace('/student/dashboard');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 409 || err.code === 'email_exists') {
          setError('Email already registered');
        } else {
          setError(err.message || 'Registration failed. Please check your details.');
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
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col items-center justify-center px-4 py-3 sm:py-6 my-auto overflow-y-auto">
      {/* Background glow */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(99,102,241,0.14) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[420px]">
        {/* Brand wordmark */}
        <div className="flex items-center justify-center gap-2 mb-2 sm:mb-3">
          <span className="text-2xl select-none">⚡</span>
          <span className="text-xl font-bold text-[var(--text-primary)] tracking-tight">SyncShift</span>
        </div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="px-5 sm:px-6 pt-4 sm:pt-5 pb-1.5 text-center">
            <h1 className="text-lg sm:text-xl font-semibold text-[var(--text-primary)] tracking-tight">Create your account</h1>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Start balancing your university timetable and work shifts
            </p>
          </div>

          {/* OAuth Buttons & Divider placed ABOVE email form */}
          <div className="px-4 sm:px-5 pt-2 pb-0">
            <OAuthButtons captchaToken={captchaToken} />
            <OAuthDivider text="OR" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-4 sm:px-5 pb-4 sm:pb-5 pt-1 space-y-2.5 sm:space-y-3">
            {/* Email */}
            <div className="space-y-1">
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
                className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg px-3.5 py-2 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
              />
            </div>

            {/* Password */}
            <div className="space-y-1">
              <label htmlFor="password" className="block text-xs font-medium text-[var(--text-secondary)]">
                Password
              </label>
              <div className="relative w-full">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="Min. 8 characters"
                  className="w-full bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg pl-3.5 pr-10 py-2 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
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

              {/* Password strength meter */}
              {password.length > 0 && (
                <div className="space-y-0.5 pt-0.5">
                  <div className="flex gap-1.5 h-1">
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore >= 1
                          ? passwordScore === 1
                            ? 'bg-rose-500'
                            : passwordScore === 2
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-slate-200 dark:bg-neutral-800'
                      }`}
                    />
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore >= 2
                          ? passwordScore === 2
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-slate-200 dark:bg-neutral-800'
                      }`}
                    />
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore === 3 ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-neutral-800'
                      }`}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span
                      className={
                        passwordCriteria.hasMinLength ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-neutral-500'
                      }
                    >
                      {passwordCriteria.hasMinLength ? '✓' : '•'} 8+ chars
                    </span>
                    <span
                      className={
                        passwordCriteria.hasUppercase ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-neutral-500'
                      }
                    >
                      {passwordCriteria.hasUppercase ? '✓' : '•'} 1 uppercase
                    </span>
                    <span
                      className={
                        passwordCriteria.hasNumber ? 'text-emerald-700 dark:text-emerald-400 font-medium' : 'text-slate-500 dark:text-neutral-500'
                      }
                    >
                      {passwordCriteria.hasNumber ? '✓' : '•'} 1 number
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label htmlFor="confirmPassword" className="block text-xs font-medium text-[var(--text-secondary)]">
                  Confirm Password
                </label>
                {passwordsMatch !== null && (
                  <span
                    className={`text-[10px] font-medium ${
                      passwordsMatch ? 'text-emerald-500 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400'
                    }`}
                  >
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </span>
                )}
              </div>
              <div className="relative w-full">
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="Re-enter password"
                  className={`w-full bg-[var(--bg-input)] border rounded-lg pl-3.5 pr-10 py-2 text-base sm:text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 transition ${
                    passwordsMatch === false
                      ? 'border-rose-500/80 focus:ring-rose-500/60'
                      : 'border-[var(--border-color)] focus:ring-indigo-500/60 focus:border-indigo-500'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-1 text-xs transition cursor-pointer"
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                >
                  {showConfirmPassword ? (
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

            {/* Timezone & Limit Grid on larger screens */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {/* Timezone */}
              <div className="space-y-1">
                <label htmlFor="timezone" className="block text-xs font-medium text-[var(--text-secondary)]">
                  Timezone
                </label>
                <CustomSelect
                  id="timezone"
                  options={TIMEZONE_OPTIONS}
                  value={timezone}
                  onChange={(val) => setTimezone(String(val))}
                  searchable={true}
                  size="sm"
                  placeholder="Select timezone..."
                />
              </div>

              {/* Weekly Work Limit */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label htmlFor="weeklyLimit" className="block text-xs font-medium text-[var(--text-secondary)]">
                    Weekly limit
                  </label>
                  <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-300 bg-indigo-500/10 border border-indigo-500/30 px-1.5 py-0.2 rounded">
                    {weeklyLimit}h/wk
                  </span>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <input
                    id="weeklyLimit"
                    type="range"
                    min={1}
                    max={40}
                    step={1}
                    value={weeklyLimit}
                    onChange={(e) => setWeeklyLimit(Number(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* Terms Checkbox */}
            <div className="flex items-start gap-2 pt-0.5">
              <input
                id="terms"
                type="checkbox"
                required
                checked={agreeTerms}
                onChange={(e) => {
                  setAgreeTerms(e.target.checked);
                  if (error) setError(null);
                }}
                className="mt-0.5 h-4 w-4 rounded border-[var(--border-color)] bg-[var(--bg-input)] text-indigo-600 focus:ring-indigo-500 cursor-pointer accent-indigo-600 shrink-0"
              />
              <label htmlFor="terms" className="text-xs text-[var(--text-secondary)] select-none cursor-pointer">
                I agree to the terms and privacy policy
              </label>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-start gap-2 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-700/60 rounded-lg px-3 py-2 break-words"
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
                  <span>Creating account…</span>
                </>
              ) : (
                <span>Create account</span>
              )}
            </button>
          </form>

          {/* Footer note */}
          <div className="px-5 sm:px-6 pb-3 sm:pb-4 text-center border-t border-[var(--border-color)] pt-2.5 sm:pt-3">
            <p className="text-xs text-[var(--text-secondary)]">
              Already have an account?{' '}
              <Link
                href="/login"
                className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium cursor-pointer transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </motion.div>

        {/* Back to landing */}
        <p className="mt-2.5 sm:mt-3 text-center text-xs text-[var(--text-muted)]">
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
