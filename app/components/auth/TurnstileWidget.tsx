'use client';

import React, { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: string | HTMLElement,
        options: {
          sitekey: string;
          callback?: (token: string) => void;
          'error-callback'?: () => void;
          'expired-callback'?: () => void;
          theme?: 'light' | 'dark' | 'auto';
          size?: 'normal' | 'compact' | 'flexible';
        }
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
    onTurnstileLoaded?: () => void;
  }
}

interface TurnstileWidgetProps {
  onVerify: (token: string) => void;
  onError?: () => void;
  onExpire?: () => void;
  className?: string;
  resetKey?: number;
}

// The backend enforces CAPTCHA policy. Never supply a public test key or mock success implicitly.
const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim();

export function TurnstileWidget({
  onVerify,
  onError,
  onExpire,
  className = '',
  resetKey = 0,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [isScriptLoaded, setIsScriptLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const callbacks = useRef({ onVerify, onError, onExpire });
  useEffect(() => { callbacks.current = { onVerify, onError, onExpire }; }, [onVerify, onError, onExpire]);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) return;

    if (typeof window === 'undefined') return;

    if (window.turnstile) {
      setIsScriptLoaded(true);
      return;
    }

    const scriptId = 'cf-turnstile-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;
    const created = !script;
    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
    }
    const loaded = () => setIsScriptLoaded(true);
    const failed = () => { setFailed(true); callbacks.current.onVerify(''); callbacks.current.onError?.(); };
    script.addEventListener('load', loaded);
    script.addEventListener('error', failed);
    if (created) document.head.appendChild(script);
    return () => { script.removeEventListener('load', loaded); script.removeEventListener('error', failed); };
  }, []);

  useEffect(() => {
    if (!isScriptLoaded || !TURNSTILE_SITE_KEY || !containerRef.current || !window.turnstile) {
      return;
    }

    // Clean up previous instance if already rendered
    if (widgetIdRef.current) {
      try {
        window.turnstile.remove(widgetIdRef.current);
      } catch {
        // ignore
      }
      widgetIdRef.current = null;
    }

    try {
      const id = window.turnstile.render(containerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        theme: 'auto',
        size: 'flexible',
        callback: (token: string) => {
          setFailed(false);
          callbacks.current.onVerify(token);
        },
        'error-callback': () => {
          setFailed(true);
          callbacks.current.onVerify('');
          callbacks.current.onError?.();
        },
        'expired-callback': () => {
          callbacks.current.onVerify('');
          callbacks.current.onExpire?.();
        },
      });
      widgetIdRef.current = id;
    } catch {
      setFailed(true);
      callbacks.current.onVerify('');
    }

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          // ignore
        }
        widgetIdRef.current = null;
      }
    };
  }, [isScriptLoaded]);

  useEffect(() => {
    if (resetKey && widgetIdRef.current !== null && window.turnstile) {
      callbacks.current.onVerify('');
      window.turnstile.reset(widgetIdRef.current);
    }
  }, [resetKey]);

  if (!TURNSTILE_SITE_KEY) {
    // Hidden in local dev when no site key is configured
    return null;
  }

  return (
    <div className={`w-full min-w-0 my-2 ${className}`}>
      <div ref={containerRef} className="w-full min-w-0" />
      {failed && <p role="alert" className="text-xs text-rose-500 mt-2">Security verification could not load. Refresh the page and try again.</p>}
    </div>
  );
}
