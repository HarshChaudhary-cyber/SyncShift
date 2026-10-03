import type { UserProfile, ClassSummary } from './api';
export function safeReturnUrl(value: unknown, fallback?: string): string;
export function verifySession(getProfile: () => Promise<UserProfile>, getMemberships: () => Promise<ClassSummary[]>, previous?: {user: UserProfile | null; memberships: ClassSummary[]} | null): Promise<{status: 'authenticated' | 'unauthenticated' | 'error'; user: UserProfile | null; memberships: ClassSummary[]; error: string | null; verified: boolean}>;
