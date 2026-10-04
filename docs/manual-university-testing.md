# SyncShift Manual University Testing Guide

This guide details how to seed, verify, reset, and manually test SyncShift's multi-tenant academic workflows, university login, and shared class synchronization.

---

## 1. Quick Start Commands

All commands are executed from the `backend/` directory using the project's Python virtual environment.

### A. Run Database Migrations
Ensures the local SQLite/PostgreSQL schema is at Alembic head:
```powershell
# Windows PowerShell
.\.venv\Scripts\alembic.exe upgrade head
```

### B. Seed the Realistic Demo Dataset
Seeds two connected universities (`APEX` and `BEACON`), academic departments, terms, rooms, subjects, sections, timetables, professors, students, personal planner tasks, and shared workspaces:
```powershell
.\.venv\Scripts\python.exe seed_demo.py --verify
```

### C. Reset Demo-Owned Data Only
Safely removes all records associated with `.example` domains and demo university codes (`APEX`, `BEACON`) without dropping tables or wiping existing user data:
```powershell
.\.venv\Scripts\python.exe seed_demo.py --reset
```

---

## 2. Seeded Test Accounts (Local Demo Only)

The seed script creates deterministic test accounts. All credentials are for **local demo use only**:

| Role | University | Email | Enrollment / Roll No | Password | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | Apex Institute of Technology | `admin@apex.example` | — | `ApexAdminPass2026!` | Full administrative access to Apex |
| **Professor** | Apex Institute of Technology | `prof.turing@apex.example` | — | `AlanTuringPass2026!` | Primary professor teaching CS101 & CS201 |
| **Student (Primary)** | Apex Institute of Technology | `student.maya@apex.example` | `00101` | `MayaStudentPass2026!` | Enrolled in Dr. Turing's sections |
| **Student (Unrelated)** | Apex Institute of Technology | `student.liam@apex.example` | `00102` | `LiamStudentPass2026!` | Enrolled only in EE101; cannot see CS101 |
| **Student (Cross-University)** | Beacon State University | `marcus@beacon.example` | `00101` | `MarcusBeaconPass2026!` | Same roll number `00101`, different institution |
| **Super Admin (Beacon)** | Beacon State University | `admin@beacon.example` | — | `BeaconAdminPass2026!` | Admin for Beacon State University |

*(Note: The local credentials JSON file is generated at `backend/.demo-credentials.json` and is strictly excluded from Git.)*

---

## 3. University Authentication Flow

### A. Enrollment Number Login
1. Navigate to `/login`.
2. Enter enrollment number `00101` in the input field labeled **"University email or enrollment/roll number"**.
3. Because `00101` exists at both **Apex Institute** and **Beacon State**, SyncShift requires university selection.
4. Select **Apex Institute of Technology** from the university selector dropdown.
5. Enter password `MayaStudentPass2026!`.
6. Click **Sign in**. The user is authenticated as student Maya Lin, with permissions derived from verified database membership.

### B. University Email Login
1. Enter `prof.turing@apex.example` and password `AlanTuringPass2026!`.
2. Click **Sign in**.
3. The user is redirected to the professor / faculty portal with full teaching schedule controls.

### C. Password Visibility Control
Click the eye icon (`EyeIcon` / `EyeSlashIcon`) inside the password field to toggle password visibility.

---

## 4. Step-by-Step Testing Scenarios

### Scenario 1: Admin Assigns Professor and Enrolls Student
1. Sign in as `admin@apex.example`.
2. Navigate to **University > Sections** (`/university/sections`).
3. Select section **CS101-SEC-A**.
4. Confirm Dr. Alan Turing is assigned as instructor and Maya Lin is enrolled.
5. Navigate to **University > Timetables** (`/university/timetables`). Confirm the Autumn 2026 master timetable is active with published meetings.

### Scenario 2: Professor Changes an Authorized Shared Class Time
1. Sign in as `prof.turing@apex.example`.
2. Navigate to **Classes** (`/classes`) and open **Algorithms & Data Structures (CS101-SEC-A)**.
3. In the class workspace, view the class events and official scheduled meetings.
4. As instructor, add or modify a class event (e.g. adjust start time from `14:00` to `15:00`).
5. Save the event changes.

### Scenario 3: Enrolled Student Sees the Updated Official Class
1. Sign in as primary student `student.maya@apex.example` (or using enrollment number `00101` + Apex).
2. Open **Calendar** (`/student/calendar` or `/calendar`).
3. **Expected Result**: Maya Lin sees the updated class occurrence reflecting the new time (`15:00`).
4. **Update & Refresh Mechanism**:
   - Updates are read-through from the authoritative database source (`ClassEvent` / `CourseMeeting`).
   - The calendar displays the change upon page load, route transition, or returning to the active browser tab (which triggers `verifySession` and refetches calendar data). SyncShift does not use continuous background WebSockets.

### Scenario 4: Student Cannot Edit University-Managed Classes
1. While logged in as `student.maya@apex.example`, view the shared class block on the calendar.
2. Official shared classes have negative block IDs (synthesized from the timetable / workspace).
3. Attempting to edit or delete the official class via personal block actions is blocked by the UI and rejected with `403 Forbidden` / `404 Not Found` by the backend.

### Scenario 5: Unrelated Student Does Not Gain Access
1. Sign in as `student.liam@apex.example` (enrollment `00102`).
2. Liam is enrolled only in `EE101-SEC-A`.
3. Navigate to `/classes`. Liam sees only `EE101` and does not see `CS101`.
4. Attempting to navigate directly to `/classes/{cs101_workspace_id}` returns `404 Not Found` or `403 Forbidden`.

### Scenario 6: Professor Private Tasks Are Isolated
1. Log in as `prof.turing@apex.example`.
2. Open **Planner / Tasks** (`/planner`).
3. Dr. Turing has private tasks ("Finalize Midterm Exam Questions", "Doctor Appointment").
4. Log out and log in as `student.maya@apex.example`.
5. Check `/student/tasks` and `/student/calendar`.
6. **Expected Result**: None of Dr. Turing's private tasks or appointments appear on Maya's schedule.

### Scenario 7: Student Private Tasks Are Isolated
1. As Maya Lin, add a personal task ("Implement Red-Black Tree in C++") and view her campus tutoring shift.
2. Log out and log in as Dr. Turing.
3. Check Dr. Turing's planner and calendar.
4. **Expected Result**: Maya's personal tasks and work shifts are strictly private to her account.

### Scenario 8: Cross-University Tenant Isolation
1. Sign in as Beacon student `marcus@beacon.example` (enrollment `00101` at Beacon).
2. Attempt to view Apex timetable (`/university/timetables`) or Apex classes (`/classes/{apex_workspace_id}`).
3. **Expected Result**: The backend rejects cross-tenant requests with `403 Forbidden` or `404 Not Found`.

---

## 5. Automated Verification Suites

Run the complete test suite verifying seeding, isolation, authentication, and permissions:
```powershell
# Backend focused demo & multi-tenant scenario tests
.\.venv\Scripts\pytest.exe test_demo_dataset_and_scenarios.py -v

# Backend university login suite
.\.venv\Scripts\pytest.exe test_university_login.py -v

# Frontend lint & build
cd ..\app
npx eslint --quiet
npm run build
```
