# Landing page feature-to-source audit

Inspected implementation on 2026-10-05, starting at `7c9d8bf`. Source inspection establishes supported scope; this is not end-to-end certification of every backend operation.

| Capability | Status | Source and boundary |
| --- | --- | --- |
| Student dashboard/calendar | Implemented | `app/components/unified/Dashboard.tsx`, `CalendarPage.tsx`, `app/context/CalendarContext.tsx`: published classes alongside private items. |
| Classes, publication, announcements | Implemented | `ClassDetail.tsx`, `Classes.tsx`, `backend/app/routers/classes.py`, `services/class_workspaces.py`: membership and instructor checks; learners see published events. |
| Subjects, credits, professor profiles | Implemented, data-dependent | `SubjectDetails.tsx`, `ProfilePage.tsx`, `backend/app/routers/academic_experience.py`: missing information explicitly marked not supplied. Professional fields shared within institution. |
| Teaching progress | Implemented | `TeachingDashboard.tsx`, `SubjectDetails.tsx`: lecture outcomes recorded explicitly; elapsed dates do not imply delivery. |
| Tasks and study planning | Implemented | `app/app/planner/page.tsx`, `backend/app/routers/tasks.py`, `student_planning.py`: owner-scoped tasks, separate preview/apply operations. |
| University administration | Implemented | `AdminArea.tsx`, `app/app/university/*`, `backend/app/routers/academic_admin.py`, `services/academic_access.py`: verified active super-admin membership required. |
| Timetable versions, impact, publication | Implemented | `routers/timetables.py`, `services/timetable_version_service.py`, `services/impact_analysis.py`: authorised review/publish workflow. |
| Audit and oversight | Implemented | `academic_admin.py`, `audit_logs.py`, `university_analytics.py`: academic changes/official teaching load, not private-task surveillance. |
| Privacy boundaries | Implemented in application access controls | `routers/blocks.py` uses owner-scoped store operations and `_require_personal_block`; `tasks.py` supplies authenticated `user_id`; `class_workspaces.py` checks memberships. No claim about database operators or security certification. |
| Notifications/updates | Implemented with dependencies | `app/app/notifications/page.tsx`, `CalendarContext.tsx`, `services/timetable_notification_service.py`, `reminders.py`: fetched schedules and notifications, no guaranteed live sync. Email/push depend on configuration/preferences. |
| AI assistant | Implemented with dependencies | `SyncShiftAssistant.tsx`, `backend/app/services/assistant_app.py`, `assistant_tools.py`, `assistant.py`: app help, authorised schedule tools, supported actions; some personal moves execute directly. University changes require confirmation. No blanket autonomy or claim that every action needs approval. |
| Sign up | Implemented | `app/app/signup/page.tsx`, `backend/app/routers/auth.py`: registration creates an account with no university membership. Invitations/membership assign university roles separately. Existing `/signup` is valid; OAuth buttons are not restored. |
| Guaranteed file parsing / conflict-free schedules | Unsupported absolute claims | Removed certainty and instant zero-delay claims. Extraction depends on source content and configured services. |
| Free forever / testimonials / customer counts | Unsubstantiated | Removed rather than inventing evidence. |
| Country-specific legal/work/visa compliance | Unsupported positioning | Removed regional marketing and legal assurances. A personal work-hour preference is not legal advice. |

## Content and visual sources

The page describes three connected role experiences, class publishing and private plans. Product previews are explicitly synthetic. Removed regional messaging, pricing promises, fabricated testimonials/statistics, and absolute parsing/conflict claims. The fictional campus and static SVG are original procedural work. No reference video was supplied. No third-party models, textures, photographs, logos, private account data, or paid assets are used.
