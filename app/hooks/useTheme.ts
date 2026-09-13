'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { api, getAuthToken } from '@/lib/api';

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

export interface UseThemeReturn {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  changeTheme: (newTheme: Theme) => void;
  toggleTheme: () => void;
}

export function useTheme(): UseThemeReturn {
  const [theme, setTheme] = useState<Theme>('dark');
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('dark');
  const isInitialized = useRef(false);

  // Helper to compute and apply active theme to <html>
  const applyTheme = useCallback((t: Theme) => {
    if (typeof window === 'undefined') return 'dark' as ResolvedTheme;

    const root = document.documentElement;
    let effective: ResolvedTheme = 'dark';

    if (t === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      effective = prefersDark ? 'dark' : 'light';
    } else {
      effective = t;
    }

    root.setAttribute('data-theme', effective);
    if (effective === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    setResolvedTheme(effective);
    return effective;
  }, []);

  // Initial load from localStorage on client mount
  useEffect(() => {
    const saved = localStorage.getItem('syncshift-theme') as Theme | null;
    const initialTheme: Theme = saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'dark';
    setTheme(initialTheme);
    applyTheme(initialTheme);
    isInitialized.current = true;
  }, [applyTheme]);

  // Listen to OS color scheme changes when theme is 'system'
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemChange = () => {
      const currentSaved = (localStorage.getItem('syncshift-theme') as Theme) || 'dark';
      if (currentSaved === 'system') {
        applyTheme('system');
      }
    };

    mediaQuery.addEventListener('change', handleSystemChange);
    return () => mediaQuery.removeEventListener('change', handleSystemChange);
  }, [applyTheme]);

  // User initiated theme change
  const changeTheme = useCallback((newTheme: Theme) => {
    setTheme(newTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('syncshift-theme', newTheme);
      applyTheme(newTheme);

      // Asynchronously sync preference to backend if authenticated
      const token = getAuthToken();
      if (token) {
        api.updateProfile({ theme: newTheme }).catch(() => {
          // Fail silently if offline or token expired
        });
      }
    }
  }, [applyTheme]);

  // Quick toggle between light and dark modes
  const toggleTheme = useCallback(() => {
    const next: Theme = resolvedTheme === 'dark' ? 'light' : 'dark';
    changeTheme(next);
  }, [resolvedTheme, changeTheme]);

  return {
    theme,
    resolvedTheme,
    changeTheme,
    toggleTheme,
  };
}
