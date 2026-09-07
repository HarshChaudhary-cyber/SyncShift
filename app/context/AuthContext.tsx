'use client';

import React, { createContext, useContext } from 'react';
import { useAuth, UseAuthReturn } from '@/hooks/useAuth';

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<UseAuthReturn | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

/**
 * Wrap the app (or specific subtrees) with <AuthProvider> to give all
 * descendants access to authentication state via useAuthContext().
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

// ─── Consumer hook ────────────────────────────────────────────────────────────

/**
 * Access auth state anywhere beneath <AuthProvider>.
 * Throws if used outside the provider — fail loudly in development.
 */
export function useAuthContext(): UseAuthReturn {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuthContext must be used within an <AuthProvider>');
  }
  return ctx;
}
