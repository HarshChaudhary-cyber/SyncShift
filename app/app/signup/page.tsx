'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthContext } from '@/context/AuthContext';
import { ApiError } from '@/lib/api';

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
  const { status, register: authRegister } = useAuthContext();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [timezone, setTimezone] = useState('Europe/London');
  const [tzSearch, setTzSearch] = useState('');
  const [weeklyLimit, setWeeklyLimit] = useState(20);
  const [agreeTerms, setAgreeTerms] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, redirect to calendar
  useEffect(() => {
    if (status === 'authenticated') {
      router.replace('/calendar');
    }
  }, [status, router]);

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
      await authRegister(email.trim(), password, timezone, weeklyLimit);
      router.replace('/calendar');
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
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Spinner size={32} />
          <p className="text-neutral-400 text-sm">Checking your session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center px-4 py-12">
      {/* Background glow */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(99,102,241,0.14) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-md">
        {/* Brand wordmark */}
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <span className="text-3xl select-none">⚡</span>
          <span className="text-2xl font-bold text-white tracking-tight">SyncShift</span>
        </div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 pt-6 pb-2 text-center">
            <h1 className="text-xl font-semibold text-white tracking-tight">Create your account</h1>
            <p className="text-xs text-neutral-400 mt-1">
              Start balancing your university timetable and work shifts
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Email */}
            <div className="space-y-1">
              <label htmlFor="email" className="block text-xs font-medium text-neutral-300">
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
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3.5 py-2 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
              />
            </div>

            {/* Password */}
            <div className="space-y-1">
              <label htmlFor="password" className="block text-xs font-medium text-neutral-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="Min. 8 characters"
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3.5 py-2 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition"
              />

              {/* Password strength meter */}
              {password.length > 0 && (
                <div className="space-y-1 pt-1">
                  <div className="flex gap-1.5 h-1.5">
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore >= 1
                          ? passwordScore === 1
                            ? 'bg-rose-500'
                            : passwordScore === 2
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-neutral-800'
                      }`}
                    />
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore >= 2
                          ? passwordScore === 2
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-neutral-800'
                      }`}
                    />
                    <div
                      className={`flex-1 rounded-full transition-colors ${
                        passwordScore === 3 ? 'bg-emerald-500' : 'bg-neutral-800'
                      }`}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-neutral-400">
                    <span
                      className={
                        passwordCriteria.hasMinLength ? 'text-emerald-400' : 'text-neutral-500'
                      }
                    >
                      {passwordCriteria.hasMinLength ? '✓' : '•'} 8+ chars
                    </span>
                    <span
                      className={
                        passwordCriteria.hasUppercase ? 'text-emerald-400' : 'text-neutral-500'
                      }
                    >
                      {passwordCriteria.hasUppercase ? '✓' : '•'} 1 uppercase
                    </span>
                    <span
                      className={
                        passwordCriteria.hasNumber ? 'text-emerald-400' : 'text-neutral-500'
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
                <label htmlFor="confirmPassword" className="block text-xs font-medium text-neutral-300">
                  Confirm Password
                </label>
                {passwordsMatch !== null && (
                  <span
                    className={`text-[10px] font-medium ${
                      passwordsMatch ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </span>
                )}
              </div>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="Re-enter password"
                className={`w-full bg-neutral-800 border rounded-lg px-3.5 py-2 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-2 transition ${
                  passwordsMatch === false
                    ? 'border-rose-500/80 focus:ring-rose-500/60'
                    : 'border-neutral-700 focus:ring-indigo-500/60 focus:border-indigo-500'
                }`}
              />
            </div>

            {/* Timezone */}
            <div className="space-y-1">
              <label htmlFor="timezone" className="block text-xs font-medium text-neutral-300">
                Timezone
              </label>
              <select
                id="timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition cursor-pointer"
              >
                {filteredTimezones.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Weekly Work Limit */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label htmlFor="weeklyLimit" className="block text-xs font-medium text-neutral-300">
                  Weekly work-hour limit
                </label>
                <span className="text-xs font-mono text-indigo-300 bg-indigo-950/60 border border-indigo-800/40 px-2 py-0.5 rounded">
                  {weeklyLimit}h / week
                </span>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <input
                  id="weeklyLimit"
                  type="range"
                  min={1}
                  max={40}
                  step={1}
                  value={weeklyLimit}
                  onChange={(e) => setWeeklyLimit(Number(e.target.value))}
                  className="flex-1 accent-indigo-500 cursor-pointer"
                />
              </div>
              <p className="text-[11px] text-neutral-500">
                SyncShift flags warnings when your shifts exceed this visa or study threshold.
              </p>
            </div>

            {/* Terms Checkbox */}
            <div className="flex items-start gap-2.5 pt-1">
              <input
                id="terms"
                type="checkbox"
                required
                checked={agreeTerms}
                onChange={(e) => {
                  setAgreeTerms(e.target.checked);
                  if (error) setError(null);
                }}
                className="mt-0.5 h-4 w-4 rounded border-neutral-700 bg-neutral-800 text-indigo-600 focus:ring-indigo-500 cursor-pointer accent-indigo-600"
              />
              <label htmlFor="terms" className="text-xs text-neutral-300 select-none cursor-pointer">
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
                  className="flex items-start gap-2 text-xs text-rose-300 bg-rose-950/60 border border-rose-700/60 rounded-lg px-3.5 py-2.5"
                >
                  <span className="shrink-0 mt-0.5">⚠️</span>
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-colors shadow-md shadow-indigo-950/40 cursor-pointer"
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
          <div className="px-6 pb-6 text-center border-t border-neutral-800/80 pt-4">
            <p className="text-xs text-neutral-400">
              Already have an account?{' '}
              <Link
                href="/login"
                className="text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </motion.div>

        {/* Back to landing */}
        <p className="mt-5 text-center text-xs text-neutral-500">
          <Link href="/" className="hover:text-neutral-300 transition-colors">
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
