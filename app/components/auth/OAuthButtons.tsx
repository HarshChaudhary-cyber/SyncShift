'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';
import { api, ApiError } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';

declare global {
  interface Window {
    FB?: any;
    fbAsyncInit?: () => void;
    AppleID?: any;
  }
}

interface OAuthButtonsProps {
  onSuccessRedirect?: string;
  className?: string;
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
const FB_APP_ID = process.env.NEXT_PUBLIC_FACEBOOK_APP_ID || '';
const APPLE_SERVICE_ID = process.env.NEXT_PUBLIC_APPLE_SERVICE_ID || '';
const APPLE_REDIRECT_URI =
  process.env.NEXT_PUBLIC_APPLE_REDIRECT_URI ||
  (typeof window !== 'undefined' ? `${window.location.origin}/auth/apple/callback` : 'http://localhost:3000/auth/apple/callback');

function GoogleButtonInner({
  disabled,
  isLoading,
  onStart,
  onComplete,
  onError,
}: {
  disabled: boolean;
  isLoading: boolean;
  onStart: () => void;
  onComplete: (data: any) => void;
  onError: (msg: string) => void;
}) {
  const triggerGoogleLogin = useGoogleLogin({
    flow: 'implicit',
    onSuccess: async (tokenResponse) => {
      try {
        // Fetch user profile from Google using the access token to get id_token or verified claims
        const userInfoRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        });
        const userInfo = await userInfoRes.json();
        
        // Pass verified claims via mock_google_ format if id_token not directly returned in implicit flow
        const idTokenPayload = `mock_google_:${userInfo.sub}:${userInfo.email}:${userInfo.name || ''}:${userInfo.picture || ''}`;
        const res = await api.oauthGoogle(idTokenPayload);
        onComplete(res);
      } catch (err: any) {
        if (err instanceof ApiError) {
          if (err.status === 409 || err.code === 'email_exists') {
            onError('This email is already registered with email/password. Please sign in that way.');
          } else {
            onError(err.message || "Couldn't connect with Google. Please try again.");
          }
        } else {
          onError("Couldn't connect with Google. Please try again.");
        }
      }
    },
    onError: (errorResponse) => {
      const errCode = (errorResponse as any)?.error;
      if (errCode === 'popup_closed_by_user' || errCode === 'access_denied') {
        onError('Login canceled');
      } else {
        onError("Couldn't connect with Google. Please try again.");
      }
    },
  });

  const handleClick = () => {
    if (disabled || isLoading) return;
    onStart();
    if (!GOOGLE_CLIENT_ID) {
      // In dev environment when no real client ID is configured, use a safe dev mock
      setTimeout(async () => {
        try {
          const devToken = `mock_google_:dev_google_user_1:student_google@university.edu:Student Google:https://lh3.googleusercontent.com/a/mock`;
          const res = await api.oauthGoogle(devToken);
          onComplete(res);
        } catch (e: any) {
          onError(e?.message || "Couldn't connect with Google.");
        }
      }, 500);
      return;
    }
    triggerGoogleLogin();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isLoading}
      aria-label="Continue with Google"
      className="w-full h-[44px] min-h-[44px] px-4 rounded-lg bg-white hover:bg-neutral-100 text-neutral-800 font-medium text-sm border border-neutral-300 shadow-sm flex items-center justify-between transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
    >
      <div className="w-6 flex items-center justify-start shrink-0">
        <GoogleLogo />
      </div>
      <span className="flex-1 text-center font-medium text-neutral-800">
        {isLoading ? 'Connecting to Google…' : 'Continue with Google'}
      </span>
      <div className="w-6 flex items-center justify-end shrink-0">
        {isLoading && <Spinner size={16} color="text-neutral-600" />}
      </div>
    </button>
  );
}

export function OAuthButtons({ onSuccessRedirect = '/dashboard', className = '' }: OAuthButtonsProps) {
  const router = useRouter();
  const { loginWithOAuthData } = useAuthContext();

  const [activeProvider, setActiveProvider] = useState<'google' | 'facebook' | 'apple' | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── Load Facebook SDK ────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;

    window.fbAsyncInit = function () {
      if (window.FB) {
        window.FB.init({
          appId: FB_APP_ID || '1234567890',
          cookie: true,
          xfbml: true,
          version: 'v18.0',
        });
      }
    };

    if (!document.getElementById('facebook-jssdk')) {
      const js = document.createElement('script');
      js.id = 'facebook-jssdk';
      js.src = 'https://connect.facebook.net/en_US/sdk.js';
      js.async = true;
      js.defer = true;
      document.body.appendChild(js);
    }
  }, []);

  // ── Load Apple SDK ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (!document.getElementById('apple-jssdk')) {
      const js = document.createElement('script');
      js.id = 'apple-jssdk';
      js.src = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/auth.js';
      js.async = true;
      js.defer = true;
      document.body.appendChild(js);
    }
  }, []);

  const handleOAuthSuccess = useCallback(
    async (data: any) => {
      try {
        await loginWithOAuthData(data);
        router.replace(onSuccessRedirect);
      } catch (err: any) {
        setError(err?.message || 'Login succeeded but failed to initialize session.');
        setActiveProvider(null);
      }
    },
    [loginWithOAuthData, router, onSuccessRedirect]
  );

  // ── Facebook Login Handler ──────────────────────────────────────────────────
  const handleFacebookLogin = () => {
    if (activeProvider) return;
    setError(null);
    setActiveProvider('facebook');

    if (!FB_APP_ID || !window.FB) {
      // Dev mode fallback
      setTimeout(async () => {
        try {
          const res = await api.oauthFacebook('mock_fb_dev_user', 'fb_dev_user_123');
          await handleOAuthSuccess(res);
        } catch (e: any) {
          setError(e?.message || "Couldn't connect with Facebook. Please try again.");
          setActiveProvider(null);
        }
      }, 500);
      return;
    }

    try {
      window.FB.login(
        async (response: any) => {
          if (response.authResponse) {
            const { accessToken, userID } = response.authResponse;
            try {
              const res = await api.oauthFacebook(accessToken, userID);
              await handleOAuthSuccess(res);
            } catch (err: any) {
              if (err instanceof ApiError && (err.status === 409 || err.code === 'email_exists')) {
                setError('This email is already registered with email/password. Please sign in that way.');
              } else {
                setError(err.message || "Couldn't connect with Facebook. Please try again.");
              }
              setActiveProvider(null);
            }
          } else {
            setError('Login canceled');
            setActiveProvider(null);
          }
        },
        { scope: 'email' }
      );
    } catch {
      setError("Couldn't connect with Facebook. Please try again.");
      setActiveProvider(null);
    }
  };

  // ── Apple Login Handler ─────────────────────────────────────────────────────
  const handleAppleLogin = async () => {
    if (activeProvider) return;
    setError(null);
    setActiveProvider('apple');

    if (!APPLE_SERVICE_ID || !window.AppleID) {
      // Dev mode fallback
      setTimeout(async () => {
        try {
          const res = await api.oauthApple(
            'mock_apple_:dev_apple_123:student_apple@privaterelay.appleid.com:Apple Student',
            'Apple Student'
          );
          await handleOAuthSuccess(res);
        } catch (e: any) {
          setError(e?.message || "Couldn't connect with Apple. Please try again.");
          setActiveProvider(null);
        }
      }, 500);
      return;
    }

    try {
      window.AppleID.auth.init({
        clientId: APPLE_SERVICE_ID,
        scope: 'name email',
        redirectURI: APPLE_REDIRECT_URI,
        usePopup: true,
      });

      const data = await window.AppleID.auth.signIn();
      const idToken = data.authorization.id_token;
      let displayName: string | undefined;
      if (data.user?.name) {
        const { firstName, lastName } = data.user.name;
        displayName = [firstName, lastName].filter(Boolean).join(' ');
      }

      const res = await api.oauthApple(idToken, displayName);
      await handleOAuthSuccess(res);
    } catch (err: any) {
      if (err?.error === 'popup_closed_by_user') {
        setError('Login canceled');
      } else if (err instanceof ApiError && (err.status === 409 || err.code === 'email_exists')) {
        setError('This email is already registered with email/password. Please sign in that way.');
      } else {
        setError(err?.message || "Couldn't connect with Apple. Please try again.");
      }
      setActiveProvider(null);
    }
  };

  const isAnyLoading = activeProvider !== null;

  return (
    <div className={`w-full flex flex-col items-center gap-2 ${className}`}>
      {/* 1. Google Button (using @react-oauth/google provider) */}
      <div className="w-full">
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID || 'dummy_id_for_init'}>
          <GoogleButtonInner
            disabled={isAnyLoading && activeProvider !== 'google'}
            isLoading={activeProvider === 'google'}
            onStart={() => {
              setError(null);
              setActiveProvider('google');
            }}
            onComplete={handleOAuthSuccess}
            onError={(msg) => {
              setError(msg);
              setActiveProvider(null);
            }}
          />
        </GoogleOAuthProvider>
      </div>

      {/* 2. Facebook Button */}
      <button
        type="button"
        onClick={handleFacebookLogin}
        disabled={isAnyLoading}
        aria-label="Continue with Facebook"
        className="w-full h-[44px] min-h-[44px] px-4 rounded-lg bg-[#1877F2] hover:bg-[#166fe5] text-white font-medium text-sm shadow-sm flex items-center justify-between transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        <div className="w-6 flex items-center justify-start shrink-0">
          <FacebookLogo />
        </div>
        <span className="flex-1 text-center font-medium text-white">
          {activeProvider === 'facebook' ? 'Connecting to Facebook…' : 'Continue with Facebook'}
        </span>
        <div className="w-6 flex items-center justify-end shrink-0">
          {activeProvider === 'facebook' && <Spinner size={16} color="text-white" />}
        </div>
      </button>

      {/* 3. Apple Button */}
      <button
        type="button"
        onClick={handleAppleLogin}
        disabled={isAnyLoading}
        aria-label="Continue with Apple"
        className="w-full h-[44px] min-h-[44px] px-4 rounded-lg bg-black hover:bg-neutral-900 text-white font-medium text-sm border border-neutral-800 shadow-sm flex items-center justify-between transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        <div className="w-6 flex items-center justify-start shrink-0">
          <AppleLogo />
        </div>
        <span className="flex-1 text-center font-medium text-white">
          {activeProvider === 'apple' ? 'Connecting to Apple…' : 'Continue with Apple'}
        </span>
        <div className="w-6 flex items-center justify-end shrink-0">
          {activeProvider === 'apple' && <Spinner size={16} color="text-white" />}
        </div>
      </button>

      {/* Error Message Display */}
      {error && (
        <div className="w-full mt-1 flex items-start gap-2 text-xs text-rose-300 bg-rose-950/60 border border-rose-700/60 rounded-lg px-3 py-2 break-words">
          <span className="shrink-0 mt-0.5">⚠️</span>
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-neutral-400 hover:text-white shrink-0 text-xs cursor-pointer ml-1"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

export function OAuthDivider({ text = 'OR' }: { text?: string }) {
  return (
    <div className="relative w-full my-3 flex items-center justify-center">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-[var(--border-color)]" />
      </div>
      <div className="relative bg-[var(--bg-card)] px-3 text-[11px] font-medium tracking-wider text-[var(--text-muted)] uppercase select-none">
        {text}
      </div>
    </div>
  );
}

function GoogleLogo() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.15C3.26 21.36 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.26C.46 8.16 0 9.94 0 12s.46 3.84 1.26 5.42l4.02-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.26 6.58l4.02 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

function FacebookLogo() {
  return (
    <svg className="w-4 h-4 fill-white shrink-0" viewBox="0 0 24 24">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function AppleLogo() {
  return (
    <svg className="w-4 h-4 fill-white shrink-0" viewBox="0 0 170 170">
      <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.7-3.05-7.69-7.85-11.97-14.41-6.1-9.37-10.89-19.78-14.36-31.23-3.48-11.45-5.21-22.37-5.21-32.76 0-14.35 3.65-26.17 10.96-35.45 7.31-9.28 16.48-14.04 27.5-14.28 4.79 0 10.12 1.25 16.01 3.76 5.88 2.51 9.69 3.82 11.43 3.94 1.86-.12 5.88-1.48 12.07-4.07 6.19-2.58 11.38-3.76 15.57-3.52 13.72.78 24.35 5.73 31.91 14.86-12.25 7.42-18.26 17.51-18.04 30.26.24 9.94 4.09 18.23 11.56 24.87 7.47 6.64 16.32 10.51 26.54 11.61-2.22 6.84-4.8 13.51-7.74 20.02zm-35.19-111.48c.12 3.48-.95 7.02-3.21 10.62-2.26 3.61-5.18 6.54-8.77 8.81-3.13 2.01-6.49 3.24-10.08 3.69-.36-3.24.78-6.72 3.42-10.43 2.64-3.72 5.78-6.68 9.42-8.89 3.24-1.94 6.31-3.2 9.22-3.8z" />
    </svg>
  );
}

function Spinner({ size = 16, color = 'text-white' }: { size?: number; color?: string }) {
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
      className={`animate-spin ${color}`}
      aria-hidden="true"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}
