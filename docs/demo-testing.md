# Local SyncShift demo

The canonical command is `backend/seed_demo.py`. `backend/seed_demo_data.py` redirects to it. The old Northbridge and Apex/Beacon seed data is historical and is not selected for deletion by email domain or university code.

## Database and seed

The existing `backend/syncshift.db` has 2,740 users, including 17 `@apex.example`, 2 `@beacon.example`, and 5 `@northbridge.edu` accounts. Their provenance cannot be proved from their addresses, so they are preserved. A local copy is at `backend/syncshift-before-syncshift-fixes-20261004.db`. The fresh demo uses `backend/syncshift-demo.db`.

From `backend` in PowerShell:

```powershell
$env:ENV = 'development'
$env:DATABASE_URL = 'sqlite:///./syncshift-demo.db'
# First run only: .\.venv\Scripts\python.exe -c "import secrets; from pathlib import Path; Path('.demo-secret').write_text(secrets.token_urlsafe(48))"
$env:JWT_SECRET = (Get-Content -Raw .demo-secret).Trim()
$env:SECRET_KEY = $env:JWT_SECRET
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe seed_demo.py --verify
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, from `app`:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
npm run dev
```

Open `http://localhost:3000/login`. Use email or a student identifier with the correct university selected. Demo credentials use fixed testing passwords (`SyncAdmin2026!`, `SyncTeacher1!2026`, `SyncTeacher2!2026`, `SyncStudent1!2026`, `SyncStudent2!2026`) and are stored in Git-ignored `backend/.demo-credentials.json`. `--date YYYY-MM-DD` sets the seed date; its default is the university-local date in Europe/London. A second seed run updates/preserves data and verifies credentials. `--verify` verifies stored credentials. `python seed_demo.py --reset` removes demo records cleanly without dropping tables.

The dataset configures SyncShift Demo University (SSDEMO), departments, subjects, sections, rooms, terms, published and draft timetables, shared class events, enrollments, teacher assignments, study and preparation tasks, appointments, notifications and preferences. Teacher 1 (Dr. Asha Rao) teaches Arjun's CS sections. Teacher 2 (Dr. Daniel Carter) teaches Math and Computing sections. Meera shares MATH101 with Arjun, but has separate advanced coursework and independent shifts.

## Password recovery

Public recovery always returns a generic response. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, and `PASSWORD_RESET_PUBLIC_URL` (the trusted frontend origin) to email 30-minute links. Without SMTP, no recovery token is issued. For a provider-only or inaccessible local account, an operator must verify the owner outside SyncShift and run `python setup_account_password.py --email <address> --identity-verified` from a trusted shell. The password is prompted securely; it is never given a default. Password changes revoke existing access tokens.

## Roles and refresh

`super_admin` can manage university users, faculty, subjects, sections, rooms, departments, terms, timetables, settings, and audit history. `admin` retains permitted operational management but cannot access super-admin-only settings or audit history. Professors can manage only their assigned teaching workspaces. Students cannot access management APIs or edit official classes. Private tasks are scoped to their owner, including from administration views.

Class and timetable reads use fresh API requests. Existing browser pages require reload or focus refresh to show changes; no live push behavior has been verified. To exercise the connected API flows without changing the manual demo database, run `python verify_syncshift_demo_api.py`; it clones the demo database into `syncshift-e2e.db` first.
