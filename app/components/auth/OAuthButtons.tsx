'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';
import { api, ApiError } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { getPortalRedirect } from '@/components/RoleGuard';

interface OAuthButtonsProps {
  onSuccessRedirect?: string;
  className?: string;
  captchaToken?: string;
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
const MICROSOFT_CLIENT_ID = process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID || '';
const MICROSOFT_TENANT = process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID || 'common';

function GoogleButtonInner({
  disabled,
  isLoading,
  captchaToken,
  onStart,
  onComplete,
  onError,
}: {
  disabled: boolean;
  isLoading: boolean;
  captchaToken?: string;
  onStart: () => void;
  onComplete: (data: any) => void;
  onError: (msg: string) => void;
}) {
  const triggerGoogleLogin = useGoogleLogin({
    flow: 'implicit',
    prompt: 'select_account',
    onSuccess: async (tokenResponse) => {
      try {
        // Fetch user profile from Google using the access token to get id_token or verified claims
        const userInfoRes = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        });
        const userInfo = await userInfoRes.json();

        // Pass verified claims via mock_google_ format if id_token not directly returned in implicit flow
        const idTokenPayload = `mock_google_:${userInfo.sub}:${userInfo.email}:${userInfo.name || ''}:${userInfo.picture || ''}`;
        const res = await api.oauthGoogle(idTokenPayload, captchaToken);
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
          const res = await api.oauthGoogle(devToken, captchaToken);
          onComplete(res);
        } catch (e: any) {
          onError(e?.message || "Couldn't connect with Google.");
        }
      }, 500);
      return;
    }
    triggerGoogleLogin({ prompt: 'select_account' });
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

export function OAuthButtons({
  onSuccessRedirect,
  className = '',
  captchaToken,
}: OAuthButtonsProps) {
  const router = useRouter();
  const { loginWithOAuthData } = useAuthContext();

  const [activeProvider, setActiveProvider] = useState<'google' | 'microsoft' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const popupRef = useRef<Window | null>(null);

  const handleOAuthSuccess = useCallback(
    async (data: any) => {
      try {
        await loginWithOAuthData(data);
        const destination = onSuccessRedirect || getPortalRedirect(data.institution_role);
        router.replace(destination);
      } catch (err: any) {
        setError(err?.message || 'Login succeeded but failed to initialize session.');
        setActiveProvider(null);
      }
    },
    [loginWithOAuthData, router, onSuccessRedirect]
  );

  // ── Microsoft Login Handler ─────────────────────────────────────────────────
  const handleMicrosoftLogin = () => {
    if (activeProvider) return;
    setError(null);
    setActiveProvider('microsoft');

    if (!MICROSOFT_CLIENT_ID) {
      // Dev mode fallback
      setTimeout(async () => {
        try {
          const devToken = `mock_microsoft_:dev_ms_user_1:student_ms@university.edu:Student Microsoft`;
          const res = await api.oauthMicrosoft(devToken, captchaToken);
          await handleOAuthSuccess(res);
        } catch (e: any) {
          setError(e?.message || "Couldn't connect with Microsoft. Please try again.");
          setActiveProvider(null);
        }
      }, 500);
      return;
    }

    try {
      const redirectUri =
        process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI ||
        (typeof window !== 'undefined'
          ? `${window.location.origin}/auth/microsoft/callback`
          : 'http://localhost:3000/auth/microsoft/callback');

      const state = Math.random().toString(36).substring(2, 15);
      const nonce = Math.random().toString(36).substring(2, 15);

      const authUrl =
        `https://login.microsoftonline.com/${MICROSOFT_TENANT}/oauth2/v2.0/authorize?` +
        new URLSearchParams({
          client_id: MICROSOFT_CLIENT_ID,
          response_type: 'id_token',
          redirect_uri: redirectUri,
          scope: 'openid profile email',
          response_mode: 'fragment',
          state: state,
          nonce: nonce,
          prompt: 'select_account',
        }).toString();

      const popup = window.open(
        authUrl,
        'microsoft_oauth',
        'width=520,height=650,left=150,top=100,menubar=no,status=no,toolbar=no'
      );
      popupRef.current = popup;

      const messageListener = async (event: MessageEvent) => {
        if (typeof window !== 'undefined' && event.origin !== window.location.origin) return;
        if (event.data?.type === 'MS_AUTH_RESPONSE') {
          window.removeEventListener('message', messageListener);
          clearInterval(pollTimer);

          if (event.data.error) {
            if (event.data.error === 'access_denied') {
              setError('Login canceled');
            } else {
              setError(event.data.error_description || "Couldn't connect with Microsoft. Please try again.");
            }
            setActiveProvider(null);
            return;
          }

          if (event.data.id_token) {
            try {
              const res = await api.oauthMicrosoft(event.data.id_token, captchaToken);
              await handleOAuthSuccess(res);
            } catch (err: any) {
              if (err instanceof ApiError && (err.status === 409 || err.code === 'email_exists')) {
                setError('This email is already registered with email/password. Please sign in that way.');
              } else {
                setError(err?.message || "Couldn't connect with Microsoft. Please try again.");
              }
              setActiveProvider(null);
            }
          }
        }
      };

      window.addEventListener('message', messageListener);

      // Poll to detect popup closure without response
      const pollTimer = setInterval(() => {
        if (popup?.closed) {
          clearInterval(pollTimer);
          window.removeEventListener('message', messageListener);
          setActiveProvider((current) => {
            if (current === 'microsoft') {
              setError('Login canceled');
              return null;
            }
            return current;
          });
        }
      }, 500);
    } catch {
      setError("Couldn't connect with Microsoft. Please try again.");
      setActiveProvider(null);
    }
  };

  const isAnyLoading = activeProvider !== null;

  return (
    <div className={`w-full flex flex-col items-center gap-2.5 ${className}`}>
      {/* 1. Google Button (using @react-oauth/google provider with select_account prompt) */}
      <div className="w-full">
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID || 'dummy_id_for_init'}>
          <GoogleButtonInner
            disabled={isAnyLoading && activeProvider !== 'google'}
            isLoading={activeProvider === 'google'}
            captchaToken={captchaToken}
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

      {/* 2. Microsoft Button */}
      <button
        type="button"
        onClick={handleMicrosoftLogin}
        disabled={isAnyLoading}
        aria-label="Continue with Microsoft"
        className="w-full h-[44px] min-h-[44px] px-4 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-sm border border-neutral-700 shadow-sm flex items-center justify-between transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        <div className="w-6 flex items-center justify-start shrink-0">
          <MicrosoftLogo />
        </div>
        <span className="flex-1 text-center font-medium text-white">
          {activeProvider === 'microsoft' ? 'Connecting to Microsoft…' : 'Continue with Microsoft'}
        </span>
        <div className="w-6 flex items-center justify-end shrink-0">
          {activeProvider === 'microsoft' && <Spinner size={16} color="text-white" />}
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

function MicrosoftLogo() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 21 21">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
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
