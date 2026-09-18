'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { getPortalRedirect } from '@/components/RoleGuard';

export default function MicrosoftCallbackPage() {
  const router = useRouter();
  const { loginWithOAuthData } = useAuthContext();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // 1. Parse fragment params (#id_token=... or #error=...) or query params (?id_token=... or ?error=...)
    const hash = window.location.hash.startsWith('#') ? window.location.hash.substring(1) : '';
    const hashParams = new URLSearchParams(hash);
    const searchParams = new URLSearchParams(window.location.search);

    const idToken = hashParams.get('id_token') || searchParams.get('id_token');
    const errCode = hashParams.get('error') || searchParams.get('error');
    const errDesc = hashParams.get('error_description') || searchParams.get('error_description');

    // 2. If opened in a popup by OAuthButtons, communicate back to opener
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(
        {
          type: 'MS_AUTH_RESPONSE',
          id_token: idToken,
          error: errCode,
          error_description: errDesc,
        },
        window.location.origin
      );
      window.close();
      return;
    }

    // 3. If standard full-page redirect flow
    if (errCode) {
      if (errCode === 'access_denied') {
        router.replace('/login?error=Login canceled');
      } else {
        setError(errDesc || 'Microsoft authentication failed.');
      }
      return;
    }

    if (!idToken) {
      setError('No authentication token received from Microsoft.');
      return;
    }

    // Exchange token with backend
    (async () => {
      try {
        const res = await api.oauthMicrosoft(idToken);
        await loginWithOAuthData(res);
        router.replace(getPortalRedirect(res.institution_role));
      } catch (err: unknown) {
        if (err instanceof ApiError && (err.status === 409 || err.code === 'email_exists')) {
          router.replace('/login?error=' + encodeURIComponent('This email is already registered with email/password. Please sign in that way.'));
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Couldn't connect with Microsoft. Please try again.");
        }
      }
    })();
  }, [loginWithOAuthData, router]);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-8 shadow-2xl space-y-4">
        {error ? (
          <>
            <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/10 border border-rose-500/25 flex items-center justify-center text-2xl">
              ⚠️
            </div>
            <h2 className="text-base font-semibold text-rose-400">Authentication Issue</h2>
            <p className="text-xs text-[var(--text-secondary)]">{error}</p>
            <button
              onClick={() => router.replace('/login')}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              ← Back to Login
            </button>
          </>
        ) : (
          <>
            <div className="w-8 h-8 mx-auto border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-[var(--text-secondary)]">Completing sign in with Microsoft…</p>
          </>
        )}
      </div>
    </div>
  );
}
