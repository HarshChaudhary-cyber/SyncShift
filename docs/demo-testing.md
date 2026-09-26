# Local demo testing

Open http://localhost:3000/login and use email/password sign-in.

| Role | Email | Password |
| --- | --- | --- |
| Student (full personal dataset) | alex.taylor@student.northbridge.edu | Student2026! |
| Student (lighter dataset) | jordan.lee@student.northbridge.edu | Student2026! |
| Administrator | admin@northbridge.edu | Northbridge2026! |
| Faculty | faculty@northbridge.edu | Faculty2026! |
| Professor with assigned classes | sarah.jenkins@northbridge.edu | Faculty2026! |

These are fictional local demo accounts. The university timezone is Europe/London.
New student accounts default to GBP; existing accounts retain their currency and
profile settings (Alex currently displays INR). Log out before switching roles.

## Suggested scenarios

- **Dashboard and calendar:** use Alex to inspect recurring classes, work shifts,
  study sessions, earnings and workload. Navigate to the week of 28 September 2026.
- **Conflicts:** Monday's Python Practice (14:00–16:00) overlaps the cafe shift
  (15:00–18:00). Move a sample event and rerun conflict detection.
- **Study planning:** six tasks include upcoming assignments, overdue work, and
  completed work. The four `Demo:` task deadlines are relative to the first seed run.
  Try planning a pending assignment, then mark progress.
- **Courses:** Alex has two personal demo courses. The institution has four academic
  courses, four sections, three rooms, three departments and student enrollments.
- **Institutional timetable:** published version 1 contains seven course meetings.
  Draft version 2 moves Monday Computer Networks to 15:00–16:30. As admin, preview
  its impact, review it and try the publication workflow. Publishing changes demo data.
- **Faculty/professor portals:** use Sarah's professor account for assigned CS301/CS302
  meetings; use the faculty account to explore the faculty role.
- **Notifications and preferences:** Alex has an in-app timetable notification,
  afternoon study preferences and a constraint protecting work shifts.
- **Profile and sessions:** edit the demo profile, change appearance, reload, log out,
  and sign back in to check persistence.
- **Exports/imports and assistant:** use the sample schedule as input for these flows.
  External AI, email delivery, browser push and OAuth still require their own setup;
  sample data does not verify those integrations.

## Seeding and local setup

The seed adds missing records without resetting passwords, deleting existing data,
or overwriting changes made during testing. A repeated run was checked for duplicate
users, blocks, tasks, academic courses, meetings, versions and enrollments.

For a normally migrated local backend, run `python seed_demo_data.py` from `backend`.
For Docker, rebuild the backend image after changing the script, then run:

```sh
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python seed_demo_data.py
docker compose up -d
```

The seed requires a database at the current Alembic revision. It no longer creates
tables without a migration record. Do not blindly stamp existing databases: the
local recovery on 26 September 2026 followed model-read and integrity checks and
saved `/data/syncshift-before-demo-1790437509.db` in the Docker SQLite volume first.

Local Compose leaves Turnstile keys blank by default. To test CAPTCHA, set
`NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `CAPTCHA_SECRET_KEY` and `CAPTCHA_ENFORCE=true`
with a matching pair of provider keys, then recreate the containers.

## Verified so far

- Email login for student, admin, faculty and professor roles through the live API.
- Student dashboard response and detection of the deliberate Monday overlap.
- Repeated seeding preserves record counts.
- Browser email login opens Alex's student dashboard on localhost:3000 with the
  sample shift and conflict visible.

Observed issues to include in your testing: some dashboard cards show zero or blank
values while the weekly summary shows populated totals; the academic overview shows
no enrolled sections despite the seeded enrollment records. These UI issues have not
been fixed as part of adding sample data.

The scenarios above are a manual test guide, not a claim that every feature passed.
