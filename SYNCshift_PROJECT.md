# SyncShift — Master Project Specification

## 1. Project Identity

**SyncShift** is an existing full-stack scheduling, timetable optimization, and university-student coordination platform.

### Primary goal

SyncShift helps students combine:
- university classes
- part-time work
- study sessions
- daily-life constraints

It also aims to help universities create feasible academic timetables while considering:
- room capacity
- faculty availability
- course/section requirements
- student constraints
- work-related conflicts
- academic rules

### Portfolio goal

This is a GitHub portfolio project intended to demonstrate:
- full-stack development
- relational database design
- REST API design
- scheduling algorithms
- constraint satisfaction / optimization
- responsible AI integration
- secure multi-user architecture
- testing
- deployment
- technical documentation

**Engineering depth and correctness are more important than feature count.**

---

## 2. Product Vision

The long-term workflow is:

```text
University defines feasible academic choices
                    +
Students define constraints and preferences
                    ↓
             SyncShift engine
                    ↓
          Feasible / optimized schedule
                    ↓
          University review / override
                    ↓
                 Publish
                    ↓
        Targeted student notifications
```

SyncShift should NOT give students unlimited control over university resources.

The core product principle is:

> The university defines what is possible. Students define what works best for them. SyncShift finds the best feasible combination.

---

## 3. Target Users

### Student

Needs:
- view academic timetable
- add work shifts
- add study sessions
- set availability
- set constraints/preferences
- detect conflicts
- optimize schedule
- track workload
- track configured work-hour limits
- use AI assistant
- receive timetable-change notifications

### Professor

Future capabilities:
- view teaching schedule
- manage assigned section information
- provide availability
- receive timetable-change information
- optionally manage office hours

### University Administrator

Needs:
- manage institution
- departments
- academic terms
- courses
- sections
- rooms
- faculty
- enrollments
- timetable drafts
- optimization
- impact analysis
- manual timetable editing
- publishing
- targeted communication
- institutional analytics

---

# 4. Existing Student Platform

The project already has substantial student-side functionality. Preserve it.

Existing capabilities include:
- authentication
- email/password login
- OAuth where configured
- student dashboard
- weekly calendar
- classes
- work shifts
- drag/drop
- resize
- conflict detection
- recurring schedule work
- ICS import
- multi-format timetable import
- analytics
- schedule health
- study planning
- optimization
- notifications
- settings
- responsive UI
- dark/light theme
- GitHub workflow/version control

### Existing student architecture

```text
Next.js
   ↓
FastAPI
   ↓
PostgreSQL
```

Do not create a second student calendar architecture.

---

# 5. Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- Framer Motion
- dnd-kit
- react-hook-form
- date-fns

## Backend

- FastAPI
- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic

## Supporting systems already used/planned

- JWT authentication
- OAuth
- Gemini API
- APScheduler
- browser push
- email
- PWA/service worker
- GitHub Actions
- Docker

**Do not replace these technologies without a strong technical reason.**

---

# 6. Global Engineering Rules

## Preserve existing work

Never rebuild a working feature merely to use a different implementation.

## Backend is authoritative

Validation, authorization, schedule correctness, conflict checks, and database writes are backend responsibilities.

## API response format

Success:

```json
{
  "data": {}
}
```

Error:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

## User identity

Never trust `user_id` from the frontend.

Use the authenticated identity from the JWT/session.

## Institution identity

Never trust institution membership merely because the client sends an institution ID.

Verify membership server-side.

## Timezone

All schedule calculations use the relevant user's/institution's IANA timezone.

Examples:
- Europe/Berlin
- Europe/Rome
- Asia/Kolkata

## Deletion

Use soft delete for normal data lifecycle operations.

## AI

AI interprets and explains.
AI does not bypass deterministic business logic.

## Testing

Meaningful business-critical changes must be tested.

## Documentation

Important architectural decisions must be documented.

---

# 7. Existing Student Data Model

The existing student-side model contains concepts such as:

## users

- id
- name
- email
- password_hash
- OAuth identifiers
- avatar/display name
- timezone
- weekly_work_hour_limit
- currency
- language
- theme
- deleted_at

## courses

- id
- user_id
- code
- name
- color

## time_blocks

Core student schedule entity.

Concepts include:
- id
- user_id
- type
- course_id
- title
- location
- day_of_week
- start_time
- end_time
- effective_from
- effective_until
- is_flexible
- hourly_wage
- deleted

The student's actual calendar should continue to use this central schedule concept.

---

# 8. Existing Conflict Logic

Current interval rule:

```text
A.start < B.end
AND
B.start < A.end
```

Overlap:

```text
min(A.end, B.end) - max(A.start, B.start)
```

Existing severity concepts:
- class + class → hard
- class + shift → hard
- shift + shift → warning
- same course / different section → warning
- weekly work-hour excess → warning

Do not duplicate this business logic in multiple files or in the AI prompt.

---

# 9. New Product Direction

SyncShift will expand from a student scheduling application into a university + student platform.

```text
                    UNIVERSITY
                        │
          ┌─────────────┼─────────────┐
          │             │             │
      Academic       Resources      Faculty
      Structure      & Capacity    Availability
          │             │             │
          └─────────────┼─────────────┘
                        │
                 MASTER TIMETABLE
                        │
                        ▼
                     STUDENTS
                        │
          ┌─────────────┼─────────────┐
          │             │             │
       Courses        Work          Personal
       Choices       Shifts       Constraints
          │             │             │
          └─────────────┼─────────────┘
                        │
                  OPTIMIZATION
                        │
                        ▼
                 COMMON TIMETABLE
                        │
                  ┌─────┴─────┐
                  │           │
             IMPACT        ADMIN
             ANALYSIS      REVIEW
                  │           │
                  └─────┬─────┘
                        ▼
                     PUBLISH
                        │
                        ▼
              TARGETED NOTIFICATIONS
```

---

# 10. Institutional Architecture

Introduce a university/tenant layer.

Core foundation:

```text
institutions
institution_memberships
departments
academic_terms
```

## institutions

Potential:
- id
- name
- slug
- country
- timezone
- created_at
- updated_at
- deleted_at

## institution_memberships

Potential:
- id
- institution_id
- user_id
- role
- status
- created_at
- updated_at
- deleted_at

Roles:
- student
- professor
- admin

## departments

Potential:
- id
- institution_id
- name
- code
- description
- timestamps
- deleted_at

## academic_terms

Potential:
- id
- institution_id
- name
- academic_year
- term_type
- start_date
- end_date
- status
- timestamps
- deleted_at

Possible term states:
- draft
- upcoming
- active
- completed
- archived

Only create fields that are genuinely required by the implementation.

---

# 11. Multi-Tenancy

Each institution is an isolated tenant.

Authorization must evaluate:

```text
authenticated user
+
institution membership
+
role
```

Never authorize solely from:
- institution_id
- role
- user_id sent by client

Cross-tenant access must be denied.

Example:

```text
User A → University A
User B → University B

User A requests University B data
→ denied
```

---

# 12. Existing User Compatibility

The institutional expansion must not break existing students.

An existing student without an institution can still use personal SyncShift.

Do not create fake universities for existing users.

Joining an institution should add membership rather than replacing the personal schedule.

---

# 13. Future Academic Model

Long-term institutional hierarchy:

```text
Institution
   ↓
Department
   ↓
Course
   ↓
Course Section
   ↓
Section Meeting
   ↓
Room

Course Section
   ↓
Professor

Student
   ↓
Enrollment
   ↓
Course Section
```

A course may have multiple sections.

Example:

```text
CS301 Database Systems

Section A
Monday 10:00–12:00
Room A101

Section B
Tuesday 14:00–16:00
Room A102
```

---

# 14. Rooms and Resources

Future university scheduling must model physical resources.

Potential:

## rooms

- institution_id
- name
- building
- capacity
- room_type

## room_resources

- room_id
- resource

Examples:
- Linux machines
- networking equipment
- FPGA equipment
- laboratory equipment

Hard constraints may include:

```text
enrollment <= capacity
required resource exists
```

---

# 15. Faculty Availability

Future faculty scheduling should support:
- professor
- day
- start_time
- end_time
- optional preferences

A professor should not be assigned to an unavailable time when availability is a hard constraint.

---

# 16. Student Constraints

Students should have:

## Hard constraints

Examples:
- fixed work shift
- unavailable period
- mandatory class
- configured work limit
- non-negotiable personal constraint

## Soft preferences

Examples:
- prefer morning classes
- prefer specific days
- fewer campus days
- avoid late classes
- preserve study time
- preferred work days

Rule:

```text
Hard constraint = must satisfy
Soft preference = ranking factor
```

---

# 17. Availability Matrix

Student availability may look like:

```text
Monday
14:00–20:00
Preferred

Tuesday
Unavailable

Wednesday
16:00–21:00
Preferred

Friday
14:00–18:00
Available
```

Availability becomes input to scheduling/optimization.

---

# 18. University Baseline Timetable

University administrators can create or import a draft academic timetable.

It may contain:
- courses
- sections
- meeting times
- professors
- rooms
- capacity
- term

This timetable is the institutional baseline before student preference optimization.

---

# 19. Student Customization Workflow

Target workflow:

```text
University creates/publishes baseline
              ↓
Students access eligible courses/sections
              ↓
Students enter work/life constraints
              ↓
Students enter preferences
              ↓
SyncShift evaluates feasible choices
              ↓
Student schedule options
              ↓
Institutional optimization aggregates demand
              ↓
University reviews result
```

Students must not edit university-owned master schedule records directly.

---

# 20. Common Timetable Optimization

This is the main advanced algorithmic capability.

The engine should consider:

### University constraints
- room capacity
- room resources
- professor availability
- section capacity
- course requirements
- academic rules

### Student constraints
- work shifts
- unavailable periods
- selected courses
- work-hour constraints
- preferences

Goal:

> Find the best feasible allocation/schedule while satisfying all hard constraints and maximizing useful soft preferences.

Do not hard-code a claimed success percentage.

Report actual optimization results.

---

# 21. Optimization Metrics

Potential results:

```text
Students evaluated: 120
Conflict-free: 108
Work-compatible: 101
Capacity violations: 0
Faculty conflicts: 0
Overall score: 91/100
```

Only show metrics actually calculated.

Potential student satisfaction factors:
- work compatibility
- preferred time satisfaction
- preferred day satisfaction
- gap penalty
- workload balance
- number of campus days

Potential institutional factors:
- capacity utilization
- room utilization
- faculty feasibility
- timetable compactness
- conflict reduction

---

# 22. Admin Manual Timetable Editor

University admin should eventually have a drag-and-drop editor.

Admin can:
- move section
- change time
- change room
- manage authorized faculty assignment
- review consequences
- publish

Before committing important changes, run impact analysis.

---

# 23. Impact Analysis

Flagship feature.

Example:

Current:

```text
CS301
Monday 10:00–12:00
```

Proposed:

```text
Wednesday 14:00–16:00
```

Calculate:
- affected students
- new conflicts
- resolved conflicts
- work conflicts
- study conflicts
- capacity problems
- faculty availability
- resource problems
- preference loss
- students with no alternative

Example result:

```text
IMPACT ANALYSIS

Students affected: 47

New hard conflicts: 8
Warnings: 5
Students without alternative: 3

Room:
✓ Valid

Faculty:
✓ Available

Work compatibility:
82% → 74%

Risk:
HIGH
```

Actions:

```text
[Cancel]
[Apply anyway]
[Find safer alternative]
```

---

# 24. Timetable Versioning

Institutional timetable must be versioned.

Concept:

```text
Version 1
Version 2
Version 3
```

Potential:

```text
timetable_versions
------------------
id
institution_id
term_id
version_number
status
created_at
published_at
created_by
```

Possible statuses:
- draft
- review
- published
- archived

Versioning supports:
- audit
- comparison
- change tracking
- notifications

---

# 25. Publishing Workflow

Recommended:

```text
DRAFT
 ↓
VALIDATE
 ↓
OPTIMIZE
 ↓
REVIEW
 ↓
IMPACT ANALYSIS
 ↓
PUBLISH
 ↓
NOTIFY AFFECTED USERS
```

Draft changes should not automatically notify all students.

---

# 26. Student Enrollment

Institutional impact requires knowing who belongs to a section.

Potential:

```text
student_enrollments

student_id
course_section_id
status
enrolled_at
```

Possible states:
- requested
- enrolled
- waitlisted
- dropped

Implement only required states.

---

# 27. Capacity Management

Section and room capacity must be represented.

Example:

```text
Room capacity: 40
Enrollment: 40

Status: FULL
```

Registration beyond capacity should be prevented unless an explicit waitlist process exists.

---

# 28. Waiting List

Optional later feature.

When a section is full:

```text
40 / 40
[Join waitlist]
```

When a seat becomes available:
- identify next eligible student
- apply defined priority rules

Do not build waiting lists before core enrollment is stable.

---

# 29. Cohort and Group Preferences

Later optimization may support:
- project groups
- cohort continuity
- friends/team preferences

These should normally be soft preferences unless an institutional rule makes them hard.

---

# 30. International Student Work-Rule Module

SyncShift may track configurable work/compliance rules.

Do NOT hard-code a universal "20 hours = every country" rule.

Potential model:

```text
country
visa_category
rule_type
term_time_rule
holiday_rule
period_basis
effective_from
source
last_verified
```

Possible rule patterns:
- weekly limit
- fortnightly limit
- term-time rule
- holiday/break variation

All legal information must be verified against current authoritative sources.

SyncShift should say:

> Informational compliance tracking, not legal advice.

---

# 31. Academic Calendar and Compliance

Institutional term data should eventually distinguish:
- teaching period
- official breaks
- term dates
- holidays

Do not assume that every holiday automatically changes legal work eligibility.

The rule must be explicitly configured.

---

# 32. Student Compliance Dashboard

Example:

```text
Work hours this period

16 / 20h

80%

4h remaining
```

University-side aggregate example:

```text
International students

Within configured rule: 108
Near threshold: 9
Over configured threshold: 3
```

Use appropriate privacy controls.

---

# 33. Conversational AI Assistant

A ChatGPT-style assistant may be provided to both students and administrators.

## Student questions

- "Do I have a conflict tomorrow?"
- "When can I work for 4 hours?"
- "Add my Friday shift from 4 to 8."
- "Why did you recommend Wednesday?"
- "Plan 4 hours of Computer Networks."

## Admin questions

- "How many students are affected if I move CS301?"
- "Find a safer slot for this lab."
- "How many sections are full?"
- "What happens if I move this lecture to Wednesday?"

---

# 34. AI Architecture

Correct architecture:

```text
User message
     ↓
LLM interpretation
     ↓
Structured intent
     ↓
Pydantic validation
     ↓
Authorized backend service/tool
     ↓
Deterministic business logic
     ↓
Result
     ↓
AI explanation
     ↓
User confirmation if needed
     ↓
Backend revalidation
     ↓
Database update
```

AI must never directly write arbitrary database values.

---

# 35. AI Tools

Potential future tools:

```text
get_today_schedule()
get_week_schedule()
get_conflicts()
get_work_hours()
find_available_slots()
run_optimizer()
run_impact_analysis()
create_block()
update_block()
create_study_goal()
get_analytics()
```

Every tool must enforce authorization and validate parameters.

---

# 36. Chat History

Possible:

```text
chat_conversations
chat_messages
ai_action_logs
```

Store:
- conversation
- messages
- action metadata where useful

Do not store:
- passwords
- secrets
- tokens
- unnecessary private data

---

# 37. AI Action Confirmation

Example:

```text
You asked me to move:

Café Roma
Friday 14:00–18:00

to:

Friday 16:00–20:00

Checks:

✓ No class conflict
✓ Work limit respected
⚠ Ends later

[Cancel]
[Confirm]
```

After confirmation, the backend must validate again.

---

# 38. University Notification Engine

When a published timetable change occurs:

```text
University change
      ↓
Find affected section
      ↓
Find enrolled students
      ↓
Compare old/new timetable
      ↓
Run conflict/impact checks
      ↓
Generate targeted notifications
      ↓
Push / Email / In-App
```

Do not notify unaffected students unnecessarily.

---

# 39. Notification Example

Student:

> Your Database Systems lecture moved from Monday 10:00 to Wednesday 14:00.

If a work conflict exists:

> This change conflicts with your logged work shift.

Actions:

```text
[View change]
[Find alternative]
[Open AI Assistant]
```

---

# 40. Email and Calendar Information

Future institutional emails may include:
- course
- section
- old time
- new time
- room
- professor where appropriate
- updated calendar information
- ICS attachment where supported

Do not claim external calendar auto-update without a real integration.

---

# 41. Read Receipts

Potential later capability:

```text
Affected: 47
Delivered: 47
Opened: 43
Unread: 4
```

This is optional and should not block the core platform.

---

# 42. Institutional Analytics

Future university dashboard can report:

### Demand
- preferred times
- section demand
- overloaded time periods

### Capacity
- room usage
- section capacity
- waitlist pressure

### Conflicts
- total conflicts
- work conflicts
- academic conflicts

### Optimization
- conflict-free percentage
- student satisfaction
- manual overrides
- resource utilization

Only report actual metrics.

---

# 43. Predictive Analytics

Optional later feature.

Possible:

> This lab slot is likely to be over-demanded.

Only introduce predictive/ML functionality after sufficient historical data exists.

Do not fabricate prediction accuracy.

---

# 44. Source of Truth

### Institutional master schedule

Source of truth for university-owned academic scheduling.

### Student calendar

Source of truth for the student's personal actual schedule.

### Optimization result

Proposal until accepted/published.

### AI

Interpreter/orchestrator, never the source of truth.

---

# 45. Privacy Model

Student-private information may include:
- work shifts
- study schedule
- private constraints
- personal preferences

University-owned information may include:
- course
- section
- room
- faculty
- published timetable

Do not reveal unnecessary private student information to university users.

A student may be able to provide:

```text
Unavailable 17:00–20:00
```

without revealing why.

---

# 46. Travel / Transition Intelligence

Start simple.

Use:
- event locations
- configurable transition buffer

Example:

Class:
14:00–16:00
Location A

Work:
16:10–20:00
Location B

Transition requirement:
30 min

Result:

```text
WARNING

Available:
10 min

Required:
30 min
```

Do not claim actual travel time unless a reliable routing system is implemented.

---

# 47. Security Requirements

Protect against:
- cross-tenant access
- IDOR
- privilege escalation
- unsafe uploads
- AI prompt injection
- unauthorized AI actions
- invalid JWT
- CORS errors
- secret leakage
- raw exception leakage
- abusive AI/file endpoints

The backend must enforce authorization.

---

# 48. Audit Logging

Important actions should eventually be auditable.

Potential events:

```text
LOGIN_SUCCESS
LOGIN_FAILED
BLOCK_CREATED
BLOCK_UPDATED
BLOCK_DELETED
IMPORT_CONFIRMED
CONFLICT_RESOLVED
OPTIMIZATION_APPLIED
TIMETABLE_PUBLISHED
TIMETABLE_CHANGED
MEMBER_ADDED
MEMBER_REVOKED
AI_ACTION_CONFIRMED
SETTINGS_CHANGED
```

Never log passwords, tokens, API keys, or unnecessary personal information.

---

# 49. Testing Strategy

## Unit tests

- overlap
- recurring occurrences
- availability
- constraints
- optimizer scoring
- duplicate detection
- impact analysis

## Integration tests

- API + services + database
- enrollment
- timetable publishing
- notifications
- AI tool execution

## Security tests

- cross-tenant access
- IDOR
- role escalation
- invalid JWT
- unauthorized AI action
- unsafe upload

## E2E

```text
Admin creates timetable
↓
Student joins
↓
Student selects sections
↓
Student adds work constraints
↓
System finds feasible schedule
↓
Admin changes timetable
↓
Impact analysis runs
↓
Admin publishes
↓
Student receives notification
```

---

# 50. Repository Development Rules

Before every coding task, AI coding agents must:

1. Read this document.
2. Inspect the actual repository.
3. Identify what is already implemented.
4. Never rebuild existing features.
5. Reuse existing architecture.
6. Implement only the requested scope.
7. Test the change.
8. Report actual results.
9. Avoid unrelated changes.
10. Update project status when requested.

---

# 51. Development Roadmap

## N1 — University Foundation [✅ COMPLETED]
- institutions: ✅ Implemented (`Institution` model, Alembic migration 0011)
- memberships: ✅ Implemented (`InstitutionMembership` model with user-institution unique constraint)
- roles: ✅ Implemented (`student`, `professor`, `admin`, server-side RBAC)
- departments: ✅ Implemented (`Department` model, unique code within institution)
- academic terms: ✅ Implemented (`AcademicTerm` model, logical date range validation)
- tenant isolation: ✅ Implemented (`InstitutionContext` dependency injection, multi-tenant scoped queries)
- frontend: ✅ Implemented (`/university`, `/university/departments`, `/university/terms`, `/university/members`)
- tests: ✅ Implemented (`test_university_foundation.py`, 7 test suites, 27/27 total backend tests passing)

### N1 Implemented Architecture Record
- **Models**: `Institution`, `InstitutionMembership`, `Department`, `AcademicTerm` in `backend/app/models/`
- **Migration**: `0011_university_foundation.py`
- **Endpoints**:
  - `GET /api/v1/institutions/me` (get user institution association)
  - `POST /api/v1/institutions` (onboard new institution, creator auto-assigned as ADMIN)
  - `GET /api/v1/institutions/{id}` (read institution details)
  - `PATCH /api/v1/institutions/{id}` (update institution, ADMIN only)
  - `GET /api/v1/institutions/{id}/dashboard` (overview metrics)
  - `GET /api/v1/institutions/{id}/members` (list members, ADMIN only)
  - `GET /api/v1/institutions/{id}/members/me` (membership & role)
  - `POST /api/v1/institutions/{id}/members` (enroll member, ADMIN only)
  - `GET /api/v1/institutions/{id}/departments` (list departments)
  - `POST /api/v1/institutions/{id}/departments` (create department, ADMIN only)
  - `GET /api/v1/institutions/{id}/departments/{dept_id}` (get department)
  - `PATCH /api/v1/institutions/{id}/departments/{dept_id}` (update department, ADMIN only)
  - `DELETE /api/v1/institutions/{id}/departments/{dept_id}` (soft-delete department, ADMIN only)
  - `GET /api/v1/institutions/{id}/terms` (list terms)
  - `POST /api/v1/institutions/{id}/terms` (create term with date validation, ADMIN only)
  - `GET /api/v1/institutions/{id}/terms/{term_id}` (get term)
  - `PATCH /api/v1/institutions/{id}/terms/{term_id}` (update term, ADMIN only)
  - `DELETE /api/v1/institutions/{id}/terms/{term_id}` (soft-delete/archive term, ADMIN only)
- **Key Architecture Decisions**:
  - Server-side multi-tenancy: Every query filters by `institution_id` derived from verified membership. No client ID trust.
  - Soft-delete strategy: Entities support `deleted_at` timestamps.
  - Backward compatibility: Preserves all existing personal student schedules and features.
- **Deferred to N2**:
  - Academic courses & sections under departments
  - Professor assignments to sections
  - Physical rooms and capacity constraints

## N2 — Academic Resources (✅ COMPLETED)
- **Status**: Complete & Verified (137/137 tests passing, Next.js build clean)
- **Database Migration**: `backend/alembic/versions/0012_academic_resources.py`
- **Models Implemented**:
  - `AcademicCourse` (`academic_courses` table): scoped to `institution_id` and `department_id`, unique `(institution_id, code)` constraint, credits, level, min room capacity, required room type, soft-delete.
  - `AcademicSection` (`academic_sections` table): scoped to `course_id`, `academic_term_id`, unique `(course_id, academic_term_id, section_code)` constraint, capacity, status, soft-delete.
  - `FacultyProfile` (`faculty_profiles` table): links to existing `User` and `InstitutionMembership` (elevated to `professor` role if not already admin/professor), optional `department_id`, `employee_code`, `title`, status, soft-delete.
  - `SectionFacultyAssignment` (`section_faculty_assignments` table): links `section_id` and `faculty_id`, unique `(section_id, faculty_id)` constraint, supports roles (`instructor`, `co_instructor`, `teaching_assistant`), primary instructor flag.
  - `Room` (`rooms` table): scoped to `institution_id`, unique `(institution_id, building, room_number)` constraint, room types (`classroom`, `laboratory`, `lecture_hall`, `seminar_room`, `auditorium`, `other`), capacity (>0), basic equipment/features, status, soft-delete.
- **REST Endpoints Added**:
  - Courses: `GET/POST /api/v1/institutions/{id}/courses`, `GET/PATCH/DELETE /api/v1/institutions/{id}/courses/{course_id}`
  - Sections: `GET/POST /api/v1/institutions/{id}/sections`, `GET/PATCH/DELETE /api/v1/institutions/{id}/sections/{section_id}`
  - Faculty: `GET/POST /api/v1/institutions/{id}/faculty`, `GET/PATCH/DELETE /api/v1/institutions/{id}/faculty/{faculty_id}`
  - Faculty Assignments: `GET/POST /api/v1/institutions/{id}/sections/{sec_id}/faculty`, `DELETE /api/v1/institutions/{id}/sections/{sec_id}/faculty/{assign_id}`
  - Rooms: `GET/POST /api/v1/institutions/{id}/rooms`, `GET/PATCH/DELETE /api/v1/institutions/{id}/rooms/{room_id}`
  - Dashboard counts updated to report courses, sections, faculty, and rooms.
- **Frontend Pages Added**:
  - `/university/courses` (catalog, search, department filter, admin create/edit/archive)
  - `/university/sections` (term & course filters, capacity, instructor assignment modal)
  - `/university/faculty` (faculty directory, department filter, member promotion & assignment modal)
  - `/university/rooms` (building & type filters, capacity badge, equipment management)
- **Legacy Integration Decisions**:
  - *Duplicate Concept Identified*: Legacy `courses` table represented student-private course tags (`user_id`, `code`, `name`, `color`, `term`) linked to `time_blocks.course_id`. Modifying or deleting this table would have broken student personal schedules and tests. Institutional course model is therefore `AcademicCourse` (`academic_courses` table). In N3/N4, student enrollment in institutional sections will link student calendar events to `academic_sections`, enabling clean gradual migration without disrupting active student schedules.
  - *Calendar Integration*: Prepared existing `CalendarWeekView` and `DraggableBlock` to handle multi-source events with visual source tags (`[CLASS]`, `[WORK]`, `[PERSONAL]`, `[OTHER]`).
- **Authorization & Multi-Tenancy**:
  - Strict server-side RBAC: ADMIN has full CRUD mutations; PROFESSOR and STUDENT have read-only access to academic resources; non-members receive 403 Forbidden; unauthenticated requests receive 401 Unauthorized.
  - All foreign keys and queries are tenant-isolated against `institution_id` derived from verified credentials. Cross-tenant IDOR attacks are rejected.
- **Deferred to N3**:
  - Student enrollment in sections (`Enrollment` model)
  - Section discovery for students
  - Student institutional onboarding & availability constraints

## N3 — Student Profile + Enrollment + Constraints (✅ COMPLETED)
- **Completion Date**: 2026-09-12
- **Key Deliverables**:
  - **Student Institutional Profile (`StudentProfile`)**:
    - Extends user architecture without duplicating credentials (`User` + `InstitutionMembership(role='student')` + `StudentProfile`).
    - Tracks: `id`, `institution_id`, `user_id`, `department_id`, `student_number` (unique per institution), `program`, `year_of_study`, `status`, `created_at`, `updated_at`.
  - **Section Enrollment (`SectionEnrollment`)**:
    - Direct M:N bridge between student users and institutional `academic_sections`.
    - Concurrency-safe capacity management: uses PostgreSQL `with_for_update()` row-level locking on `academic_sections` during enrollment transactions, preventing race-condition seat overallocation.
    - Full status lifecycle (`active`, `dropped`, `waitlisted`, `completed`).
    - Enforces uniqueness on active enrollments per student/section (`uq_student_active_section_enrollment`).
    - Strict validation: student belongs to institution, section belongs to institution, section is active, academic term is active/upcoming.
  - **Student Weekly Availability (`StudentAvailability`)**:
    - Structured recurring weekly availability slots (days 0–6, `start_time < end_time`, `is_available` boolean, optional `note`).
    - Transactional replacement via `PUT /api/v1/students/me/availability` with interval overlap validation.
  - **Student Hard Constraints (`StudentConstraint`)**:
    - Strict non-negotiable boundaries: `earliest_start`, `latest_end`, `max_hours_per_day`, `protect_work_shifts`, `custom`.
    - Flagged with `is_hard=True` and `is_active=True`.
  - **Student Soft Preferences (`StudentPreference`)**:
    - Multi-factor preference weights: `preferred_time_of_day` ('morning', 'afternoon', 'evening', 'any'), `schedule_density` ('compact', 'balanced', 'spaced'), `break_preference` ('short', 'medium', 'long'), `max_days_per_week`, `prefer_free_days`, and interactive `work_study_balance_weight` (0–100 slider).
  - **Constraint Precedence Hierarchy (Documented for N5 Optimizer)**:
    1. **Tier 1: University Hard Constraints** (room capacity, mandatory lecture hours, faculty limits).
    2. **Tier 2: Student Hard Constraints** (`StudentConstraint` with `is_hard=True`).
    3. **Tier 3: Fixed Work Shifts** (`TimeBlock` with `type='shift'` and `is_flexible=False`).
    4. **Tier 4: Student Soft Preferences** (`StudentPreference` weights + `is_hard=False` constraints).
  - **Legacy System Integration**:
    - Zero duplicate tables for shifts: preserves `TimeBlock(type='shift', is_flexible=False/True)`.
    - Zero duplicate tables for personal events: preserves `TimeBlock(type='study')`.
    - Dashboard summary integration: `AcademicSummaryCard` in `/dashboard` displaying enrolled courses, section codes, credits, and direct link to academic portal.
  - **APIs Implemented**:
    - `GET /api/v1/students/me`, `PATCH /api/v1/students/me`
    - `GET /api/v1/students/me/enrollments`, `POST /api/v1/students/me/enrollments`, `DELETE /api/v1/students/me/enrollments/{id}`
    - `GET /api/v1/institutions/{id}/sections/available` (catalog with live capacity & enrollment status)
    - `GET /api/v1/students/me/availability`, `PUT /api/v1/students/me/availability`
    - `GET /api/v1/students/me/constraints`, `POST /api/v1/students/me/constraints`, `PATCH /api/v1/students/me/constraints/{id}`, `DELETE /api/v1/students/me/constraints/{id}`
    - `GET /api/v1/students/me/preferences`, `PUT /api/v1/students/me/preferences`
  - **Database Migration**:
    - `0013_student_profile_enrollment_constraints.py` (indexes, foreign keys, unique constraints, checked via upgrade/downgrade).
  - **Frontend Pages**:
    - `/student/academics` (Profile editor, enrolled sections list with drop confirmation, searchable course catalog with capacity bars)
    - `/student/availability` (Interactive 7-day recurring availability editor with templates)
    - `/student/constraints` (Hard constraints manager and soft preferences tuning panel)
  - **Verification & Regression**:
    - 7 dedicated test suites in `test_student_academics_n3.py` (100% passing).
    - Full test suite: 144/144 tests passing (zero regressions).
    - Frontend TypeScript and Next.js build: 26/26 routes successfully compiled and prerendered.
- **Deferred to N4**:
  - Baseline timetable generation engine
  - Section meetings (weekly lecture/lab slots)
  - Room scheduling & conflict engine for institutional timetables
  - Common timetable optimization (N5)

## N4 — University Baseline Timetable [✅ COMPLETED]
- timetable creation/import & management: ✅ Implemented (`Timetable` model)
- active baseline vs draft status: ✅ Implemented
- validation & conflict engine: ✅ Implemented (`timetable_validator.py`, room capacity, room/faculty/section overlaps)
- section meetings: ✅ Implemented (`CourseMeeting` model with recurring weekly slots)
- UX & Brand refinement: ✅ Implemented (navigation simplified to 5 items, Academic Resources Hub, centerpiece timetable)

## N5 — Unified Schedule & Smart Planning [✅ COMPLETED]
- university timetable as authoritative baseline anchor: ✅ Implemented (classes never moved or duplicated)
- holistic schedule synthesis: ✅ Implemented (`ScheduleContextBuilder`: classes, shifts, personal events, blackouts, constraints, tasks)
- constraint hierarchy & deterministic optimization: ✅ Implemented (`ConstraintEngine`: intervals, boundaries, buffers, deadlines)
- multi-strategy candidate generation: ✅ Implemented (`CandidateGenerator`: Balanced Week, Deep Focus, Compact Schedule)
- transparent quality scoring & explainability: ✅ Implemented (`ScheduleScorer` and `ExplanationEngine`)
- strictly read-only preview & safe apply: ✅ Implemented (`POST /preview` zero-mutation, `POST /apply` mutates only student-owned flexible items)
- full calendar & conflict engine integration: ✅ Implemented (re-verified post-apply)


## N6 — Admin Editor + Impact Analysis [✅ COMPLETED]
- drag/drop editor: ✅ Implemented (drag, resize, and edit modal triggering proposed change preview)
- impact preview: ✅ Implemented (`POST /changes/preview`, read-only, real enrolled students, O(1) batched conflict queries)
- ripple effects: ✅ Implemented (work shifts, personal events, classes, availability blackouts, hard constraints, room/faculty/capacity)
- safer alternatives: ✅ Implemented (blocked severity guidance, room/time collision reporting, stale concurrency protection)

## N7 — Versioning + Publishing
- timetable versions
- review
- publish
- change history

## N8 — Communication
- affected-student identification
- push
- email
- calendar information

## N9 — AI Assistant
- student chat
- admin chat
- history
- tool calling
- confirmations
- audit

## N10 — University Analytics
- demand
- capacity
- conflicts
- optimization results

## N11 — Security + Integration
- multi-tenant security
- privacy
- security testing
- regression suite

## N12 — Final Portfolio
- README
- architecture diagrams
- technical documentation
- screenshots
- demo dataset
- deployment
- final QA

---

# 52. MVP Definition

The university-side MVP should prove:

1. Admin creates university
2. Admin creates academic term
3. Admin creates departments
4. Admin creates courses/sections
5. Admin defines rooms/capacity
6. Student joins university
7. Student selects courses/sections
8. Student enters work constraints
9. System detects conflicts
10. System generates feasible options
11. Admin reviews timetable
12. Admin publishes timetable
13. Affected students receive notification

Not required for MVP:
- predictive ML
- advanced read receipts
- live routing
- full offline synchronization
- complex professor marketplace
- unnecessary social features

---

# 53. Current Status Tracking

Use these statuses:

```text
✅ IMPLEMENTED
🟡 PARTIAL
🔴 BROKEN
⚪ PLANNED
🚫 OUT OF SCOPE
```

Important:

This file describes product architecture and target capabilities. The actual repository determines implementation status.

Never tell a user something is implemented only because it appears in this document.

---

# 54. Feature Matrix

| Area | Current Direction | Target |
|---|---|---|
| Student Authentication | Existing | Hardened |
| Student Calendar | Existing | Advanced |
| Work Shifts | Existing | Advanced |
| Conflict Engine | Existing | Institutional-aware |
| Recurring Events | Existing/partial | Robust |
| Analytics | Existing/partial | Student + University |
| Schedule Health | Existing/partial | Integrated |
| Study Planner | Existing/partial | Integrated |
| Student Optimizer | Existing/partial | Advanced |
| Timetable Import | Existing | Advanced |
| Notifications | Existing | Institution-aware |
| AI Assistant | Existing/partial | Student + Admin |
| Institutions | ✅ IMPLEMENTED | Production-ready |
| Departments | ✅ IMPLEMENTED | Production-ready |
| Academic Terms | ✅ IMPLEMENTED | Production-ready |
| Course Sections | ✅ IMPLEMENTED (N2/N3) | Production-ready |
| Rooms | ✅ IMPLEMENTED (N2 foundation) | Production-ready |
| Faculty | ✅ IMPLEMENTED (N2 foundation) | Production-ready |
| Student Profile & Constraints | ✅ IMPLEMENTED (N3) | Production-ready |
| Enrollment | ✅ IMPLEMENTED (N3) | Production-ready |
| Common Timetable | Planned | Implemented |
| Impact Analysis | Planned | Implemented |
| Versioning | Planned | Implemented |
| Publishing | Planned | Implemented |
| University Analytics | Planned | Implemented |
| Multi-tenant Security | ✅ IMPLEMENTED (N1/N2/N3) | Hardened |
| Portfolio Documentation | Partial | Complete |

---

# 55. Portfolio Positioning

Do NOT describe SyncShift simply as:

> A calendar app.

Preferred positioning:

> **SyncShift is a full-stack scheduling and timetable optimization platform that coordinates university academic constraints with students' work and lifestyle requirements.**

Technical positioning:

> **The platform combines relational data modeling, scheduling algorithms, constraint-based optimization, impact analysis, AI-assisted interaction, targeted notifications, and secure multi-tenant architecture.**

Only use claims supported by the implemented system.

---

# 56. Academic Value

SyncShift should demonstrate:
- data modeling
- algorithms
- interval scheduling
- constraint satisfaction
- optimization
- relational databases
- REST API design
- authentication
- authorization
- background processing
- AI tool use
- testing
- software architecture

The repository should contain enough technical documentation to make these contributions understandable to a technical reviewer.

---

# 57. Architecture Decision Records

Important decisions to document:

- why Next.js
- why FastAPI
- why PostgreSQL
- why deterministic scheduling
- why AI is not trusted for business-critical decisions
- why the student's calendar remains a source of truth
- why institutions require tenant isolation
- why timetable versioning is needed
- why impact analysis happens before publishing

---

# 58. Definition of Done

A feature is complete only when:

- frontend is implemented
- backend is implemented where needed
- database is correct
- migrations are correct
- API validation exists
- authorization exists
- errors are handled
- loading/empty states exist where appropriate
- responsive behavior is checked
- relevant tests pass
- existing functionality still works
- documentation is updated where necessary

---

# 59. Final Product Story

The finished system should demonstrate:

```text
University creates academic possibilities
            ↓
Students provide real-world constraints
            ↓
SyncShift analyzes both sides
            ↓
Deterministic engine finds feasible schedules
            ↓
University reviews the result
            ↓
Admin changes are analyzed for impact
            ↓
University publishes
            ↓
Affected students are notified
            ↓
AI helps students/admins interact with the system
```

This is the core product story.

---

# 60. FINAL MASTER INSTRUCTION FOR ANTIGRAVITY

Whenever you receive a task for SyncShift:

**Read `SYNCshift_PROJECT.md` completely before changing code.**

Then:

1. Inspect the existing repository.
2. Compare actual implementation with this specification.
3. Determine what is already implemented.
4. Never rebuild existing features.
5. Reuse existing components/services.
6. Preserve existing API contracts.
7. Preserve existing student functionality.
8. Implement the requested task only.
9. Enforce authentication/authorization server-side.
10. Respect timezone rules.
11. Use soft deletes.
12. Keep AI behind validation and deterministic business logic.
13. Add database migrations through Alembic when required.
14. Run relevant tests.
15. Check for regressions.
16. Report exactly what was changed.
17. Do not claim PASS unless actually verified.

**The actual repository is the source of truth for implementation status. This document is the source of truth for product direction and architecture.**

---

# 61. Implementation Milestones: Task N4 — University Baseline Timetable

## 1. Completion Summary
Task N4 establishes the university's authoritative baseline academic timetable on the unified SyncShift platform, connecting Courses, Sections, Course Meetings, Day/Time, Faculty, and Rooms, while directly integrating scheduled class meetings into enrolled students' calendars and unified conflict detection without duplicating manual blocks in `time_blocks`.

## 2. Data Models & Schema Design
1. **`Timetable` (`timetables`)**:
   - `id`: Primary key.
   - `institution_id`: Foreign key to `institutions.id` (multi-tenant root).
   - `academic_term_id`: Foreign key to `academic_terms.id`.
   - `name`: String (unique per institution and term).
   - `status`: Baseline status (`draft`, `active`, `archived`). Activating one timetable automatically sets previous active timetables in the same term to `draft`.
   - `description`: Optional text notes.
   - `created_at`, `updated_at`, `deleted_at`: Soft-delete auditing.
   - Unique constraint: `uq_timetable_institution_term_name` on `(institution_id, academic_term_id, name)`.

2. **`CourseMeeting` (`course_meetings`)**:
   - `id`: Primary key.
   - `institution_id`: Foreign key to `institutions.id`.
   - `timetable_id`: Foreign key to `timetables.id` (CASCADE on delete).
   - `section_id`: Foreign key to `academic_sections.id`.
   - `academic_term_id`: Foreign key to `academic_terms.id`.
   - `day_of_week`: Integer (`0 = Sunday, 1 = Monday, ..., 6 = Saturday`, aligned with SyncShift standards).
   - `start_time`, `end_time`: Time fields storing local schedule hours in the institution's timezone.
   - `room_id`: Nullable foreign key to `rooms.id`.
   - `faculty_id`: Nullable foreign key to `faculty_profiles.id` (supports optional meeting-level instructor override).
   - `meeting_type`: String (`lecture`, `laboratory`, `tutorial`, `seminar`, `practical`, `other`).
   - `status`: String (`active`, `scheduled`, `cancelled`).
   - `created_at`, `updated_at`, `deleted_at`: Soft-delete auditing.

## 3. Relationships
```text
Institution
 ├── AcademicTerm
 ├── Department
 ├── Course
 │    └── Section
 │         └── CourseMeeting
 │              ├── FacultyAssignment (Primary or direct faculty override)
 │              └── Room
 └── Students
      └── Enrollment
           └── Section
                └── (materialized onto Student Calendar)
```

## 4. Validation & Conflict Detection Engine
Implements unified, deterministic interval overlap validation:
- Standard interval rule: `A.start < B.end AND B.start < A.end`. Consecutive back-to-back meetings (`A.end == B.start`) do not conflict.
- **Duration & Time Validity**: `start_time < end_time`, day in `0..6`, duration 15–480 minutes.
- **Tenant & Term Alignment**: Section, Timetable, Room, and Faculty must belong to the same institution. Section's academic term must match timetable term.
- **Room Capacity Validation**: `room.capacity >= section.capacity` (enforced with 422 `insufficient_room_capacity`).
- **Room Overlap Conflict**: Same room cannot be scheduled for overlapping meetings on the same day (409 `room_conflict`).
- **Section Overlap Conflict**: Same section cannot have overlapping meetings on the same day (409 `section_conflict`).
- **Faculty Overlap Conflict**: An instructor cannot be assigned to overlapping meetings on the same day (409 `faculty_conflict`), whether assigned directly or resolved through `SectionFacultyAssignment`.

## 5. Student Calendar Integration
- Authoritative synchronization: Enrolled students dynamically receive occurrences of scheduled section meetings in `/api/v1/students/me/schedule` and `/api/v1/week`.
- Virtualized occurrences: Materialized with negative IDs in `get_occurrences_for_range` (`type='class'`, read-only, non-tamperable by students).
- Automatic Conflict Detection: Work shifts or personal events overlapping an enrolled class meeting trigger `class_vs_shift` conflicts in `/api/v1/week` and dashboard.
- Dropping an enrollment automatically and immediately removes its meetings from the student's active schedule.

## 6. REST API Endpoints
- `GET /api/v1/institutions/{id}/timetables`: List timetables with term and status filters.
- `POST /api/v1/institutions/{id}/timetables`: Create timetable (ADMIN).
- `GET /api/v1/institutions/{id}/timetables/{tt_id}`: Timetable details with metrics.
- `PATCH /api/v1/institutions/{id}/timetables/{tt_id}`: Update metadata / status (ADMIN).
- `DELETE /api/v1/institutions/{id}/timetables/{tt_id}`: Archive timetable (ADMIN).
- `GET /api/v1/institutions/{id}/timetables/{tt_id}/meetings`: List meetings with enriched data.
- `POST /api/v1/institutions/{id}/timetables/{tt_id}/meetings`: Schedule course meeting with validation (ADMIN).
- `GET /api/v1/institutions/{id}/timetables/{tt_id}/meetings/{m_id}`: Meeting details.
- `PATCH /api/v1/institutions/{id}/timetables/{tt_id}/meetings/{m_id}`: Update meeting schedule (ADMIN).
- `DELETE /api/v1/institutions/{id}/timetables/{tt_id}/meetings/{m_id}`: Remove meeting (ADMIN).
- `GET /api/v1/students/me/schedule`: Authenticated student's official academic schedule.

## 7. Legacy Integration & Coexistence Decisions
- **`time_blocks` table**: **KEEP**. Used for student personal work shifts, study blocks, and user events.
- **`course_meetings` & `timetables`**: **INTEGRATE**. Established as the institutional source of truth for academic classes; dynamically surfaces in calendar views.
- **Manual student class blocks**: **DEPRECATE LATER**. Non-institutional / legacy users can still create standalone class blocks, but institutional students' enrolled classes flow automatically from section meetings.
- **Conflict Engine**: **KEEP & INTEGRATE**. Unified conflict detection handles overlaps across both personal shifts and institutional classes.

## 8. Features Intentionally Deferred to N5+
- Automatic timetable optimization algorithms.
- Cross-student schedule scoring.
- Admin timetable impact analysis & drag/drop rearrangement editor (Task N6).
- Version publishing / approval workflows (Task N7).
- Targeted timetable change notification dispatching (Task N8).

---

# N4 Product UX & Brand Refinement Specification

## 1. Core Brand Architecture & Messaging
SyncShift unifies the university academic schedule with individual student calendars under one cohesive mission:
- **Central Platform Purpose**: *"Connect the university timetable with real student life."*
- **Student Experience**: *"Plan classes, work, and life in one schedule."*
- **University Administrator Experience**: *"Build better timetables and understand their impact on students."*

These taglines are positioned in key headers and onboarding overviews where they clarify purpose rather than creating repetitive clutter.

## 2. University Navigation Simplification
### Before
9 top-level tabs exposed simultaneously in the header:
`Overview` | `Departments` | `Academic Terms` | `Courses` | `Sections` | `Timetables` | `Faculty` | `Rooms` | `Members`

### After
5 streamlined, conceptual navigation items:
1. **HOME** (`/university`) — Institution dashboard featuring current timetable status, active term, and task actions.
2. **TIMETABLE** (`/university/timetables`) — Visual centerpiece for viewing and editing baseline class schedules.
3. **ACADEMIC RESOURCES** (`/university/resources`) — Unified hub and sub-navigation grouping all building blocks.
4. **STUDENTS** (`/university/members`) — Campus member directory for enrolled students and instructors.
5. **ASK SYNCSHIFT** (Trigger) — Instant assistant modal for schedule diagnostics and operational queries.

## 3. Academic Resources Grouping
- **Conceptual Definition**: *"Academic Resources = the building blocks the university uses to build its timetable."*
- **Hub Directory** (`/university/resources`): Central dashboard featuring interactive cards, live resource counts, and direct actions for:
  - **Courses** (`/university/courses`): Code, name, credits, academic level, and room requirements.
  - **Sections** (`/university/sections`): Class sections, seating capacities, and instructor assignments.
  - **Faculty** (`/university/faculty`): Instructor profiles, departmental appointments, and titles.
  - **Rooms** (`/university/rooms`): Classrooms, lecture halls, and laboratories with seat limits.
  - **Departments** (`/university/departments`): Academic faculties and subject divisions.
  - **Academic Terms** (`/university/terms`): Semesters, quarters, and active calendar windows.
- **Secondary Pill Sub-navigation** (`AcademicResourcesNav`): Shared responsive navigation bar embedded across all 6 resource pages allowing instant switching without cluttering the global university layout.

## 4. Timetable as the Main Centerpiece
- Prominently spotlighted on the University Overview (`/university`) as the authoritative baseline schedule.
- Displays active term, total scheduled meetings count, sections covered, and a high-contrast primary CTA: `Open Timetable Grid →`.
- Timetable list page clearly communicates page purpose: *"See and manage your university's class schedule."*

## 5. Home / Overview Simplification & Quick Actions
- Redesigned `/university/page.tsx` around real user tasks rather than database status:
  - **View Timetable**: Opens weekly master grid.
  - **Add Class Meeting**: Opens meeting scheduler on active baseline timetable.
  - **Manage Academic Resources**: Opens Academic Resources hub.
  - **View Students**: Opens campus user and enrollment directory.
- Database jargon (such as *"Tenant Status: Data Isolated & Scoped"*) removed in favor of clean operational status indicators.

## 6. Student Side Navigation Refinement
### Primary Desktop & Mobile Navigation
1. **Home** (`/dashboard`) — Daily timeline, upcoming blocks, alerts, and workload.
2. **My Schedule** (`/calendar`) — Comprehensive weekly calendar (`"See your classes, work, and personal time together"`).
3. **My Courses** (`/student/academics`) — Institutional course enrollments, scheduled meeting times, availability, and constraints.
4. **Plan** (`/planner`) — Smart study planner discovering conflict-free study slots.
5. **Ask SyncShift** (Trigger) — Global assistant drawer for timetable and schedule assistance.

### Secondary Menu (`More ▾`)
- **Analytics** (`/analytics`) — Workload and earnings summaries.
- **Import Schedule** — Multi-format timetable import.
- **University Portal** (`/university`) — Direct access to institutional administration.
- **Settings** (`/settings`) — Notification and user preferences.

## 7. Terminology Decisions & UI Integrity
- **Human-Centric Vocabulary**: Standardized on "Classes", "Timetable", "Courses", "Students", "Faculty", "Rooms", "Sections".
- **Strictly Prohibited in UI**: `institution_id`, `tenant`, `UUID`, `database`, `API`, `schema`.
- **Progressive Disclosure**: Primary operational tasks front and center; technical filters and configuration placed inside modals and contextual actions.

## 8. Preserved Routes for 100% Backward Compatibility
All existing routes remain fully operational for bookmarks and direct navigation:
- `/university`
- `/university/timetables`
- `/university/timetables/[id]`
- `/university/resources`
- `/university/courses`
- `/university/sections`
- `/university/faculty`
- `/university/rooms`
- `/university/departments`
- `/university/terms`
- `/university/members`
- `/dashboard`
- `/calendar`
- `/student`
- `/student/academics`
- `/student/availability`
- `/student/constraints`
- `/planner`
- `/analytics`
- `/settings`
- `/settings/notifications`

---

# 58. Task N5 — Unified Schedule & Smart Planning Architecture Record

## 1. Core Concept & Authoritative Flow
Task N5 implements the smart planning layer of SyncShift:
- **University Timetable is Authoritative**: Official `CourseMeeting` slots are non-negotiable fixed anchors. They are never altered, moved, or duplicated into `time_blocks`.
- **Holistic Schedule Synthesis**:
  $$\text{Academic Schedule} + \text{Student Work} + \text{Personal Events} + \text{Availability} + \text{Constraints} + \text{Preferences} + \text{Study Tasks} \rightarrow \text{Optimized Weekly Plan}$$

## 2. Schedule States & Optimization Precedence
1. **Tier 1: University Class Meetings** (`CourseMeeting` from active enrollments): Strict anchor; immutable by student planning.
2. **Tier 2: Hard Student Commitments**:
   - Fixed work shifts (`TimeBlock.type == 'shift'`, `is_flexible == False`).
   - Fixed personal events (`TimeBlock.type == 'personal'`).
   - Unavailable blackout periods (`StudentAvailability.is_available == False`).
   - Hard constraints (`StudentConstraint.is_hard == True`: e.g. `earliest_start`, `latest_end`, `max_hours_per_day`, `day_off`).
3. **Tier 3: Task Deadlines & Buffers**:
   - Study sessions for a task must conclude before its deadline date (and before 18:00 on deadline day).
   - Minimum transition buffers (10–15 mins) enforced between events at different locations.
4. **Tier 4: Flexible Student Items (Optimizable)**:
   - Study tasks (`StudyTask` pending/scheduled).
   - Flexible work shifts (`TimeBlock.type == 'shift'`, `is_flexible == True`).
5. **Tier 5: Student Soft Preferences (Ranking & Scoring)**:
   - Preferred time of day (`morning`, `afternoon`, `evening`, `any`).
   - Schedule density (`compact`, `balanced`, `spread`).
   - Preferred days off.
   - Focus session durations.

## 3. Modular Backend Architecture (`backend/app/services/smart_planner/`)
- **`ScheduleContextBuilder`** (`context.py`): In-memory compilation of institutional meetings, work shifts, personal events, availability blackouts, hard constraints, soft preferences, and active tasks.
- **`ConstraintEngine`** (`constraints.py`): Deterministic interval overlap checking (`A.start < B.end AND B.start < A.end`), buffer validation, capacity, and deadline validation.
- **`CandidateGenerator`** (`generator.py`): Slices free gaps into 15/30-minute candidate slots generating 3 distinct strategies:
  - **Balanced Week**: Evenly distributed study with standard breaks.
  - **Deep Focus**: Consolidated 90–120m focus blocks ahead of deadlines.
  - **Compact Schedule**: Clusters sessions on existing campus days to maximize free days off.
- **`ScheduleScorer`** (`scorer.py`): Transparent quality score (0–100) based on preference match, workload balance, and focus quality. Hard conflicts yield score = 0 / invalid.
- **`ExplanationEngine`** (`explainer.py`): Generates human-friendly bulleted reasons (e.g. *"✓ Zero class conflicts"*, *"✓ Meets Friday deadline"*) and explicit trade-offs.
- **`SmartPlannerService`** (`service.py`): Coordinates read-only preview, safe atomic apply, and weekly plan revert.

## 4. Safety & Authorization Model
- **Strictly Read-Only Preview**: `POST /api/v1/students/me/planning/preview` mutates zero database records.
- **Permitted Mutations Only**: `POST /api/v1/students/me/planning/apply` writes only student-owned `TimeBlock` study records, updates associated `StudyTask` status to `'scheduled'`, and never mutates university class records.
- **Re-Verification**: Automatically re-runs conflict detection (`detect_conflicts_and_totals`) after plan application.
- **Multi-Tenant Security**: Enforces student institutional boundaries; no cross-tenant or cross-user IDOR access.

## 5. REST APIs Implemented
- `POST /api/v1/students/me/planning/preview`: Generates strategic options with change breakdown.
- `POST /api/v1/students/me/planning/apply`: Applies approved study blocks and adjustments.
- `DELETE /api/v1/students/me/planning/revert`: Rolls back planned study blocks for a week window.

## 6. Frontend Integration
- **`WeeklyPlanHero.tsx`**: Prominent hero card on `/planner` displaying week commitment counts and the primary `Plan My Week` action.
- **`PlanOptionsModal.tsx`**: Interactive multi-strategy modal displaying quality score rings, change breakdown (+X study blocks, 0 shifts moved, Y classes unchanged), explainable reasons, trade-offs, and confirmation apply button.
- **Preserved Existing Tasks**: Active task list, task creation, and single-task planning remain fully functional below the weekly planner.

## 7. Verification Results
- **Dedicated Test Suite**: `test_smart_planner_n5.py` (5/5 tests passing).
- **Full Backend Regression**: 154/154 tests passing (**100% pass rate**).
- **Frontend Build**: 28/28 routes compiled cleanly with 0 TypeScript errors.

---

# 59. Task N6 — University Timetable Editor & Impact Analysis Architecture Record

## 1. Core Workflow & Product Promise
Task N6 implements the university administrator's advanced timetable editing and "understand the impact before publishing the change" workflow:
> **Core Product Promise**: *"Make timetable changes confidently, with visibility into their impact on students."*

### Authoritative Workflow:
1. **Open Timetable**: Admin views the official weekly timetable grid (`/university/timetables/[id]`).
2. **Move/Resize/Edit Class**: Admin drags a meeting to a new time slot, resizes it, or clicks "Edit Class".
3. **Proposed Change Created**: An in-memory proposed change is generated — **no silent saving**. The UI enters "CHANGE PREVIEW" mode.
4. **Validation & Impact Analysis**: `POST /changes/preview` runs canonical institutional constraint checks and calculates student ripple effects in real-time (strictly read-only).
5. **Review Impact**: Admin reviews aggregated metrics first (students affected, new conflicts created, work shift clashes, availability blackouts, room/faculty status), with optional drill-down into sanitized student conflict details.
6. **Explicit Confirmation**: If safe, admin clicks "Apply Change". If blocked by room/faculty/capacity collisions, the change is blocked with clear guidance.
7. **Safe Atomic Apply**: `POST /changes/apply` verifies optimistic concurrency timestamps, atomically updates the database, writes an audit record, and updates student academic schedules automatically.

## 2. Proposed Change Architecture
- **Stateless In-Memory Proposal**: Represented via `TimetableChangeProposal` schema (`meeting_id`, `day_of_week`, `start_time`, `end_time`, `room_id`, `faculty_id`, `meeting_type`).
- Avoids persistent database draft pollution for fleeting drag interactions while preserving zero-mutation guarantees during preview.

## 3. Pre-Save Institutional Validation
- Direct reuse of canonical `validate_course_meeting` in `backend/app/services/timetable_validator.py`.
- Evaluates:
  - Section overlaps (cannot schedule two meetings for the same section at the same time).
  - Room occupancy collisions (room cannot be double-booked).
  - Faculty assignment collisions (instructor cannot teach two classes simultaneously).
  - Room capacity check (room capacity cannot be less than current active section enrollment).
  - Valid time ranges (`start_time < end_time`, boundary limits).
  - Institution tenant ownership.
- If any check fails, `is_blocked = True` and severity is marked `BLOCKED` with human-readable diagnostic messages.

## 4. High-Performance Impact Analysis Engine (`backend/app/services/impact_analysis.py`)
- **Real Enrolled Students**: Queries `SectionEnrollment` with `status == 'enrolled'` — never estimates from section capacity.
- **Batched, Set-Based Queries (O(1) roundtrips)**:
  - Preloads all active enrollments for the section in a single query.
  - Preloads all `TimeBlock` records (work shifts, personal commitments) for all enrolled students in a single batched query.
  - Preloads all other institutional `CourseMeeting` records for enrolled students across all their enrolled sections.
  - Preloads all `StudentAvailability` blackout periods.
  - Preloads all hard `StudentConstraint` records (`earliest_start`, `latest_end`, `max_hours_per_day`, `day_off`).
- **Deterministic Delta Calculation**:
  - Compares student conflicts at the *before* meeting slot vs. the *proposed* slot.
  - Categorizes conflicts into `new_conflicts` (created by the move) and `resolved_conflicts` (cleared by the move).
  - Standard interval overlap rule: `A.start < B.end AND B.start < A.end` (back-to-back events are conflict-free).

## 5. Impact Severity Classification
- **`BLOCKED`**: Hard institutional constraints violated (room collision, faculty collision, room capacity insufficient). Applying the change is forbidden.
- **`HIGH`**: Severe ripple effects: > 10 new student conflicts, OR > 50 affected students, OR > 5 work-shift conflicts.
- **`MEDIUM`**: Manageable ripple effects: 1–10 new student conflicts, OR 10–50 affected students.
- **`LOW`**: Minimal ripple effects: 0 new conflicts, < 10 affected students.

## 6. Privacy & Security Safeguards
- **Minimum Necessary Data**: Administrator sees operational conflict diagnostics (`student_id`, `student_name`, `conflict_type`, `conflict_source_title`, `conflict_time`).
- **Student Privacy Protected**: Hourly wages, private notes, unrelated calendar events, and sensitive constraint details are strictly stripped from responses.
- **Tenant Isolation**: All operations enforce `context.institution_id`. Cross-tenant preview and apply attempts are rejected with 403 Forbidden / 404 Not Found.
- **Authorization**: Preview and Apply are strictly restricted to institutional `ADMIN` (`require_institution_admin`).

## 7. Optimistic Concurrency Protection
- `TimetableChangeApplyRequest` accepts `expected_updated_at` (the timestamp of the meeting when the preview was generated).
- Backend compares `meeting.updated_at` against `expected_updated_at`. If another administrator altered the meeting in the interim, the transaction rejects with HTTP 409 Conflict:
  > *"This timetable changed since you reviewed it. Please review the new version before applying your change."*

## 8. Audit Trail Foundation (N7 Preparation)
- Applies updates in a single atomic database transaction.
- Writes an immutable audit entry into `audit_logs`:
  - `action = "timetable_meeting_change"`
  - `entity_type = "course_meeting"`
  - `entity_id = meeting.id`
  - `metadata_json = { "before": {...}, "after": {...}, "impact": {...} }`
- Provides the exact data foundation required for Task N7 (Timetable Versioning & Publishing).

## 9. REST API Endpoints
- `POST /api/v1/institutions/{institution_id}/timetables/{timetable_id}/changes/preview`
  - Body: `TimetableChangeProposal`
  - Response: `TimetableImpactResponse` (strictly read-only).
- `POST /api/v1/institutions/{institution_id}/timetables/{timetable_id}/changes/apply`
  - Body: `TimetableChangeApplyRequest` (includes `expected_updated_at`)
  - Response: `TimetableChangeApplyResponse` (atomic update + audit log).

## 10. Frontend User Experience
- **Timetable Page (`/university/timetables/[id]`)**:
  - Drag-and-drop (`onBlockMove`) and resize (`onBlockResize`) in `CalendarWeekView` automatically trigger impact preview.
  - Class edit modal includes a prominent "Preview Impact" button.
  - High-visibility "CHANGE PREVIEW" mode banner with active proposed slot and quick "Discard" action.
- **Impact Modal (`TimetableImpactModal.tsx`)**:
  - Clear Before/After comparison cards (day, time, room, faculty).
  - Prominent severity badge (`LOW`, `MEDIUM`, `HIGH`, `BLOCKED`).
  - Aggregated metrics first (students affected, new conflicts, work shifts, availability, room/faculty status).
  - Tabbed detail inspection: Overview, Students (with conflict type filter), Room & Capacity, Faculty.
  - Human-friendly action buttons: `Apply Change` and `Cancel` (no technical database jargon).

## 11. Student Synchronization & Calendar Integration
- Student academic schedules (`/api/v1/students/me/schedule`) pull dynamically from authoritative `CourseMeeting` records via active enrollments.
- Changing a timetable meeting immediately updates the student's unified calendar without duplicating records or creating artificial personal blocks.

## 12. Legacy Component Classification
| Component | Classification | Rationale |
|---|---|---|
| `Timetable` & `CourseMeeting` | **KEEP** | Authoritative baseline institutional scheduling models. |
| `SectionEnrollment` | **KEEP** | Canonical source of student-section enrollment relationships. |
| `timetable_validator.py` | **INTEGRATE** | Reused directly by N6 impact analysis to prevent duplicated validation logic. |
| `audit_logs` model | **INTEGRATE** | Reused as the audit trail foundation for N6 changes and future N7 versioning. |
| `CalendarWeekView` | **KEEP** | Standardized grid component for both student calendars and university timetables. |
| Legacy `Course` & `Block` models | **DEPRECATE LATER** | Preserved for backward compatibility with initial prototype; targeted for cleanup in N11. |

## 13. Verification Summary
- **N6 Test Suite**: `test_timetable_impact_n6.py` (8/8 tests passing).
  - Valid proposed change preview & conflict calculation.
  - Invalid time range rejection.
  - Room collision detection & `BLOCKED` status.
  - Faculty collision detection & `BLOCKED` status.
  - Room capacity violation detection & `BLOCKED` status.
  - Atomic apply & audit log recording.
  - Stale concurrency preview rejection (409 Conflict).
  - Tenant isolation enforcement (cross-tenant access rejection).
  - Student schedule automatic update verification.
- **Full Backend Regression**: 162/162 tests passing (**100% pass rate**, 0 regressions).
- **Frontend Production Build**: 28/28 routes compiled cleanly with zero TypeScript or ESLint errors.

## 14. Scope Boundaries (Deferred to N7+)
- Full timetable version snapshots, draft vs. published state lifecycles, and formal approval workflows (Deferred to **N7**).
- Automated targeted student notifications (email, push, in-app alerts) and read receipts (Deferred to **N8**).
- Institutional demand, capacity, and bottleneck analytics (Deferred to **N10**).


