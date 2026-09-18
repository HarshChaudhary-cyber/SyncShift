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
}

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

export function TurnstileWidget({
  onVerify,
  onError,
  onExpire,
  className = '',
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [isScriptLoaded, setIsScriptLoaded] = useState(false);

  useEffect(() => {
    // If no site key is provided in development, automatically pass dev mock token
    if (!TURNSTILE_SITE_KEY) {
      const timer = setTimeout(() => {
        onVerify('mock_captcha_pass_local_dev');
      }, 200);
      return () => clearTimeout(timer);
    }

    if (typeof window === 'undefined') return;

    if (window.turnstile) {
      setIsScriptLoaded(true);
      return;
    }

    const scriptId = 'cf-turnstile-script';
    if (!document.getElementById(scriptId)) {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.onload = () => setIsScriptLoaded(true);
      document.head.appendChild(script);
    } else {
      setIsScriptLoaded(true);
    }
  }, [onVerify]);

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
          onVerify(token);
        },
        'error-callback': () => {
          if (onError) onError();
        },
        'expired-callback': () => {
          if (onExpire) onExpire();
        },
      });
      widgetIdRef.current = id;
    } catch {
      // ignore
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
  }, [isScriptLoaded, onVerify, onError, onExpire]);

  if (!TURNSTILE_SITE_KEY) {
    // Hidden in local dev when no site key is configured
    return null;
  }

  return (
    <div className={`w-full flex justify-center my-2 min-h-[65px] ${className}`}>
      <div ref={containerRef} className="w-full max-w-[300px]" />
    </div>
  );
}
