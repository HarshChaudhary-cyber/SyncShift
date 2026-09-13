'use client';

import React, { createContext, useContext } from 'react';
import { useTheme, UseThemeReturn } from '@/hooks/useTheme';

const ThemeContext = createContext<UseThemeReturn | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const themeState = useTheme();
  return (
    <ThemeContext.Provider value={themeState}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeContext(): UseThemeReturn {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }
  return ctx;
}
