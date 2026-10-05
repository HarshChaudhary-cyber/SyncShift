# Login and visual continuity repair

Verified on 2026-10-05 against the local Docker app at `http://localhost:3000`.

## Login cause and repair

The Docker backend used `/data/syncshift-demo.db` in its named volume. Its application tables were empty and its user count was **0**. The existing accounts were in the separate host database `backend/syncshift-demo.db`. Building an image and running migrations creates the schema; it does not import the host database or create demo accounts.

A consistent SQLite backup of the existing local demo database was imported into Docker after checking that **every application table** in the destination was empty. The original host database was preserved. The imported dataset contains 19 users; SQLite integrity checking returned `ok`. No passwords, membership roles, or permission rules were changed. Docker's named volume retains this dataset across container rebuilds.

Credentials remain in the Git-ignored `backend/.demo-credentials.json`. Use the entry for `admin@ssdemo.example`, `professor.asha@ssdemo.example`, or `student.arjun@ssdemo.example`. JWT/SECRET_KEY values in `.env` are server signing secrets, not account passwords. Do not delete the database volume to fix login issues.

The backend image previously included local seed credentials/manifest files despite excluding `.env` and database files. `.dockerignore` now excludes those files for future builds. No secrets or database snapshots are committed.

## UI changes

- Added a shared SyncShift brand component and campus color tokens used by landing, account pages, and all authenticated roles.
- Login and signup now use the same responsive account frame, theme control, typography, violet accents, and original local campus illustration.
- Workspace navigation, cards, headings, focus styling, and primary buttons continue that identity. Existing navigation and role permissions are preserved.
- Failed credentials produce an accessible explanatory alert; the backend still returns the same generic authentication failure.
- Password recovery uses the existing native dialog component for focus containment, Escape dismissal, and viewport scrolling. No password was reset during testing.
- Removed the implicit Cloudflare public test key and fabricated development success token. With no site key, the frontend renders no test widget; the backend still enforces its configured CAPTCHA policy. Configured widgets retain stable callbacks across typing, clear expired/error tokens, and reset after failed login attempts. Provider failures are displayed rather than silently swallowed.

## Verification

- Local production build and Docker frontend build passed. The local frontend container was recreated with the new image; the backend and database volume were retained.
- Frontend lint passed: 0 errors, 179 warnings total. Two warnings in the CAPTCHA component concern setting state from effects when initializing an existing provider or reporting a synchronous provider failure.
- Existing frontend tests: 14 passed.
- Direct API logins with existing stored credentials returned tokens and the expected authoritative roles for student, professor, and super-admin. Tokens/passwords were not printed.
- Browser login, role-specific dashboard, and logout worked for all three roles. Incorrect credentials were rejected before a successful retry. A student signing in after the administrator was routed to the student dashboard rather than the prior restricted university settings page.
- Login: 360, 390, 768, 1024, 1366 CSS pixel widths in both light and dark themes; no measured document overflow or out-of-bounds account content.
- Signup: the same five widths in light mode, plus 360 pixels in dark mode. No account was created and no terms were accepted.
- Recovery dialog at 360 pixels fit within the viewport, was modal, and closed with Escape. No recovery request or reset was submitted.
- All three role dashboards: 360, 768, 1366 pixels, with one workspace shell and no document overflow. Additional checks covered admin university settings, student calendar and light dashboard, professor classes and planner.

Measurements: [checks.json](screenshots/auth-workspace/checks.json).

Screenshots:

- [Login, dark](screenshots/auth-workspace/login-dark.jpg)
- [Login, light](screenshots/auth-workspace/login-light.jpg)
- [Login, mobile](screenshots/auth-workspace/login-mobile.jpg)
- [Administration workspace](screenshots/auth-workspace/admin-workspace.jpg)
- [Student workspace, dark](screenshots/auth-workspace/student-workspace.jpg)
- [Student workspace, light](screenshots/auth-workspace/student-light.jpg)
- [Professor workspace](screenshots/auth-workspace/professor-workspace.jpg)

Screenshots of authenticated routes use the existing fictional demo dataset. Configured live CAPTCHA challenges, outbound recovery email, password changes, and real mobile keyboards were not exercised. No production deployment or merge was performed.
