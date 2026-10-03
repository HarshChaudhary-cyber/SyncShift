export function safeReturnUrl(value, fallback = '/dashboard') {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020]/.test(value)) return fallback;
  try {
    const decoded = decodeURIComponent(value);
    if (decoded.startsWith('//') || /[\\\u0000-\u0020]/.test(decoded)) return fallback;
    const url = new URL(value, 'https://syncshift.invalid');
    if (url.origin !== 'https://syncshift.invalid' || /^\/(login|signup|auth)(\/|$)/.test(url.pathname)) return fallback;
    return url.pathname + url.search + url.hash;
  } catch { return fallback; }
}

export async function verifySession(getProfile, getMemberships, previous = null) {
  try {
    const user = await getProfile();
    if (!user || !Number.isInteger(user.user_id) || !user.email) throw new Error('Invalid profile');
    const memberships = await getMemberships();
    if (!Array.isArray(memberships)) throw new Error('Invalid memberships');
    return { status: 'authenticated', user, memberships, error: null, verified: true };
  } catch (error) {
    if (error?.status === 401) return { status: 'unauthenticated', user: null, memberships: [], error: null, verified: false };
    return { status: previous?.user ? 'authenticated' : 'error', user: previous?.user || null,
      memberships: previous?.memberships || [], error: 'We could not verify your session. Check your connection and retry.', verified: false };
  }
}
