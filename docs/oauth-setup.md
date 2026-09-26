# Google and Microsoft sign-in setup

The OAuth buttons activate only when their public client IDs are configured.
Email and password sign-in remains available without OAuth configuration.

## Local configuration

Add the public IDs to the ignored local environment files:

`app/.env.local`:

```dotenv
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-web-client-id
NEXT_PUBLIC_MICROSOFT_CLIENT_ID=your-microsoft-application-client-id
NEXT_PUBLIC_MICROSOFT_TENANT_ID=common
```

`backend/.env`:

```dotenv
GOOGLE_CLIENT_ID=your-google-web-client-id
MICROSOFT_CLIENT_ID=your-microsoft-application-client-id
MICROSOFT_TENANT_ID=common
ALLOWED_ORIGINS=http://localhost:3000
RATE_LIMIT_ENABLED=false
```

Use the **same** Google ID in both files and the same Microsoft ID in both
files. Restart both development servers after changing environment files.
The rate limit setting above is for local development without Redis; keep
rate limiting enabled with a reachable Redis service in production.

## Provider registrations

- In Google Cloud, create or use a **Web application** OAuth client and add
  `http://localhost:3000` to its authorized JavaScript origins. See
  [Google's web OAuth setup](https://developers.google.com/identity/oauth2/web/guides/overview).
- In Microsoft Entra, add `http://localhost:3000/auth/microsoft/callback` as a
  redirect URI and enable **ID tokens** under implicit grant and hybrid flows.
  The app uses the current browser origin for this callback, so register your
  deployed origin too. If you use a single-tenant registration, set its tenant
  ID in both environment files instead of `common`. See
  [Microsoft's OpenID Connect setup](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc).

The app verifies Google tokens against the configured Google client ID and
Microsoft ID tokens against the configured Microsoft client ID, issuer, and
sign-in nonce. Provider credentials must be registered for each deployed origin.
