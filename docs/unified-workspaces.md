# Unified workspaces

Implemented on `codex/unified-class-workspaces`. Changes are intentionally uncommitted; nothing was pushed or deployed.

## Application

The authenticated shell uses `/dashboard`, `/calendar`, `/classes`, `/classes/[id]`, `/planner`, `/notifications`, and `/settings`. The account menu contains settings, preferences, sign out, and authorized advanced administration. The assistant has one entry in the shell. The landing page component is unchanged.

Legacy student dashboard, calendar, timetable, courses, planner, notifications, and settings routes redirect to their shared equivalents. University dashboard and notifications also redirect. Existing institutional configuration and approval screens remain available through advanced administration. Private work details and conflict details remain linked from Calendar; planning preferences remain linked from Planner.

## Permissions and privacy

- Creating a class makes the creator its instructor. This grants no rights in other classes or institutions.
- Class codes grant learner access only. An existing instructor can generate an email-bound learner or instructor invitation. Tokens are stored as hashes, expire in seven days, and can be accepted once. Invitation links are shared manually; email delivery is not implemented.
- Every class read and mutation checks membership on the backend. Learners cannot publish, edit, invite, announce, or manage membership. Removing the last instructor is rejected.
- Published shared events are stored once. Calendar reads overlay them beside the caller's private events. Pending edits remain private until publication; cancellation removes the shared event from subsequent calendar reads. Notifications are recorded for members.
- Calendar refreshes on focus, local schedule changes, and every minute while visible. Conflict detection and study planning use the combined schedule for its owner.
- Members see display names and class roles, not other members' email addresses, private shifts, tasks, or availability. The assistant uses the caller's schedule and published class data. Chat state resets between accounts.
- Retained institutional impact/analytics reports now exclude private shifts, availability, and personal constraints entirely. Compatibility count fields remain zero with a `private_schedules_evaluated: false` marker. Academic, room, and faculty checks remain available. Each member checks personal conflicts privately.

## Existing-data compatibility

Migration `0020` adds five class tables and a wrapper for each existing nondeleted academic section. It does not replace or delete existing users, private blocks, enrollments, meetings, or timetable versions. Compatibility roles are resolved from current enrollments, teaching assignments and institutional administration; explicit class revocation overrides them.

Published academic meetings are read from their existing authoritative records. Active unversioned baseline timetables remain visible; draft versions/baselines are excluded. Recurring academic timetable editing continues through the retained institutional approval workflow; ordinary class instructors can create and publish new workspace events but cannot bypass institutional approval to rewrite a legacy timetable. Personal imports and recurrence keep their existing workflow.

Apply `alembic upgrade head` before starting the updated backend. Back up an existing database first. The additive migration deliberately refuses destructive downgrade; rollback requires a reviewed backup. `python verify_migrations.py` creates an isolated revision-0019 database, inserts legacy records, upgrades to 0020, checks preserved record counts and wrapper creation, and exercises registration, profile, personal-event and class creation APIs.

## Authentication

Only successful server profile and membership checks establish a new authenticated session. A 401 clears the session. Network/server failures provide retry; only previously verified profiles may remain visible. OAuth responses must pass the same verification; no synthetic fallback profile is created. External/unsafe return URLs are rejected. Mock bearer-token and nonexistent/deleted-user checks are retained.

## Verification (2026-10-01–2026-10-02)

- Full backend suite: **279 passed, 21 skipped** after the institutional privacy changes.
- Focused class, impact, assistant and calendar suite: **26 passed, 2 skipped**.
- Final class/calendar regression run after compatibility-role and legacy-location edits: **9 passed**.
- Session/redirect tests: **7 passed** (`npm run test:session`).
- Frontend TypeScript and production build passed. ESLint: **0 errors**, warnings remain across the existing application and new data-loading effects.
- Populated legacy migration smoke test passed.
- On October 2, TypeScript, all 7 session tests, and the production build passed again with the final frontend edits. The preview was restarted against the same isolated demo database; saved private-event and shared-class data remained visible. Class timetable and Settings were inspected at a measured 390px CSS viewport without page-wide horizontal overflow.
- Browser: email/password login and logout; creating a class while learning in others; event draft/publication; joining as a different learner; read-only shared timetable and calendar overlay; CSV extraction/review/confirmation; editing a single recurring private occurrence. Desktop/compact layouts and the mobile dashboard/navigation were inspected, including a recoverable fetch error and successful Retry. Browser viewport overrides were inconsistent on some tabs; a complete device-matrix check is still recommended.

Skipped checks: 15 Redis-dependent tests (Redis unavailable), 2 Docker OCR tests, and 4 legacy live-server scenarios whose health probe targets `/api/v1/health` (the running service exposes `/health`). The browser checks above exercised the running application independently. Real Google/Microsoft sign-in remains unverified until real provider client IDs are configured. No AI provider credentials were used for this preview.

## Local preview

The frontend runs only on **http://localhost:3000**. The backend on port 8000 uses an isolated ignored `backend/unified-preview.db`, migrated and seeded with the repository's demo data. Existing application databases were not changed.

Demo email login: `alex.taylor@student.northbridge.edu` or `jordan.lee@student.northbridge.edu`, password `Student2026!`. Alex teaches the preview Design Studio class; Jordan joined it as a learner. Both retain their original academic enrollments. These are local demo credentials only.
