# SyncShift responsive layout verification

Date: 2026-10-04. Branch: `codex/syncshift-verify-fixes`.

## Causes and fixes

- The fixed 224px sidebar had no vertical scrolling. Its long administration navigation pushed the AI/account controls below the viewport. It now scrolls independently and keeps navigation items from compressing.
- Workspace grid tracks, schedule text, badges, forms and their implicit grid columns retained intrinsic minimum widths. Long class names and notification controls could expand their parents. Main content explicitly occupies the space beside the sidebar; grid/flex children can shrink, text wraps, actions wrap, and narrow forms/cards stack.
- The university and student layouts added horizontal padding inside an already padded AppShell. They now use one bounded content wrapper. Browser inspection found one `#workspace-content` per checked route, rather than duplicate navigation shells. University column changes use the available content width through a container query.
- The planner hero used viewport breakpoints even when the sidebar reduced its available width. Its columns now depend on workspace width.
- Wide calendars/tables need usable columns, rather than page-wide scrolling. They have bounded local scrolling containers; calendar and table regions can receive keyboard focus. The calendar toolbar and loading state also wrap.
- Settings notification rows and implicit form tracks caused measurable overflow at 360px and 768px during verification. Wrapping the controls and using `minmax(0, 1fr)` tracks resolved it. All six settings categories were rechecked after that correction.
- Fixed AI dimensions and unconstrained dialogs could exceed narrow or short viewports. Shared overlay styles bound their dimensions and allow internal scrolling. `ViewportMetrics` tracks the visual viewport when a software keyboard opens or the visible area moves. Mobile form fields use 16px text to avoid input-focus zoom.
- The date picker had a minimum width and was positioned inside clipping parents. Its popup is now portaled, positioned against visual viewport bounds, and scrolls internally when necessary. Selecting a date was verified.
- Authenticated pages previously used global horizontal overflow hiding, which could conceal clipping. That masking is removed from the workspace. Public-page decorative clipping remains scoped to public pages to preserve the landing design. Page content still scrolls vertically.

## Browser checks

Actual CSS `innerWidth` values were measured, rather than inferred from requested browser dimensions. The in-app browser reported a device pixel ratio of approximately 1.88; physical viewport overrides were calibrated accordingly. Normal checks used an 800px CSS viewport height.

| Role | Themes | CSS widths | Coverage |
| --- | --- | --- | --- |
| Super admin | Light and dark | 360, 390, 768, 1024, 1366 | Dashboard, calendar, planner, classes, settings, admin, university settings, courses, sections, faculty, rooms, departments, terms, timetable list/detail, members, students, audit logs, analytics, resources, notifications, impact analysis |
| Student | Light and dark | 360, 390, 768, 1024, 1366 | Dashboard, calendar, planner, classes/detail, settings, profile, notifications, appointments, shifts, constraints, availability, academics, conflicts, timetable, assistant |
| Professor | Light and dark | 360, 390, 768, 1024, 1366 | Dashboard, calendar, planner, classes/detail, settings, profile, notifications, appointments, shifts, constraints |
| Student settings | Light and dark | 360, 390, 768, 1024, 1366 | Account, appearance/accessibility, calendar/planner, notifications, security, privacy/data |

AI panels were additionally checked at all five widths for the three roles, including mobile upload/history controls. Representative calendar event, planner task, university course and date-picker dialogs were opened and dismissed without saving records. The professor class timetable tab was checked on mobile.

### Measurements

[Raw measurements](screenshots/responsive/measurements.json) contain 695 observations, including repeated checks. Twelve intermediate settings observations are marked `before_notification_fix`; three of these expose the earlier overflow. Their state labels can reflect the clicked tab while the preceding notification content was still visible. Final settings checks wait for the requested heading before measuring. The other 683 observations have no detected document/body overflow beyond a 1px rounding tolerance and no visible offending elements outside intentional local scrollers.

The checks compare root/body scroll widths with the root client width and inspect element rectangles. Closed, off-screen mobile navigation and children clipped by a bounded intentional `overflow-x: auto/scroll` container are excluded from the offending-element list. Horizontal overflow is visible at the authenticated root, so it is not hidden to make these checks pass.

Additional interaction checks:

- At 360px the weekly calendar had approximately 315px of available width and 931px of scrollable content. Arrow Right moved the calendar's local scroll position while document horizontal scroll remained zero.
- The calendar page retained approximately 2445px of vertical content at an 800px viewport height.
- At 360 x 300px, the AI panel occupied y=12 to y=288; its input ended at y=275. Close/send controls remained inside the visible area.
- At 360 x 300px, the planner task dialog had approximately 267px of visible height and 664px of scrollable content. The calendar event overlay also fitted the short viewport.
- Mobile task date selection updated the trigger to the selected date.
- Sidebar AI/account actions became reachable by scrolling the navigation. Permission checks and role-specific actions were not changed.

## Zoom and device limitations

Native Chrome zoom at 125% and 150% could not be verified. Windows computer use stopped because the tool could not determine the browser URL confidently enough to enforce its policy. Native interaction was stopped. The in-app browser's reliable URL/DOM access remained available for the recorded checks.

As a partial substitute, CSS widths 1093 and 911 (1366 divided by 1.25 and 1.5) were measured across dashboard, calendar, planner, classes/detail and settings for student/professor, plus admin and university settings/timetable detail for super admin. All 40 recorded observations passed. This exercises the reduced available width, but does not certify native zoom rendering or font rasterization.

A real mobile software keyboard was unavailable. Reduced-height checks at 360 x 300px verify scrolling and control bounds; actual iOS/Android keyboard behavior remains a device check. Visual viewport resize/scroll handling is implemented for those devices.

Checks used the existing local demo accounts/data on localhost, not production accounts. Every data mutation, modal workflow, calendar view or table dataset was not exhaustively retested. No backend, authorization, role permission or scheduling logic was changed.

## Screenshots

The original desktop screenshots supplied by the user are retained as before evidence. After images are browser captures with explicit physical bounds, avoiding an in-app screenshot scaling/cropping issue. Before/after desktop images use different window dimensions; they are evidence of layout behavior, not a pixel-perfect comparison.

- [Before: administration](screenshots/responsive/user-before-admin.png)
- [Before: university settings](screenshots/responsive/user-before-university-settings.png)
- [After: administration, 1366px dark](screenshots/responsive/after-admin-1366-dark.jpg)
- [After: university settings, 360px dark](screenshots/responsive/after-university-settings-360-dark.jpg)
- [After: calendar, 360px dark](screenshots/responsive/after-calendar-360-dark.jpg)
- [After: assistant, 360px dark](screenshots/responsive/after-assistant-360-dark.jpg)
- [After: assistant, 360 x 300px](screenshots/responsive/after-assistant-short-viewport.jpg)

## Build checks

- `npm run lint` in `app`: exit 0; 0 errors, 180 existing warnings.
- `npm run build` in `app`: exit 0; Next.js 16.3.4 production build and TypeScript checks passed.
- `git diff --check`: passed.
- Continued the existing branch and preserved its earlier commits. No merge or deployment performed.

## Affected files

See the list below for the complete source scope; screenshot and measurement artifacts are under `docs/screenshots/responsive`.

- `app/app/globals.css`
- `app/app/layout.tsx`
- `app/app/settings/page.tsx`
- `app/app/student/academics/page.tsx`
- `app/app/student/availability/page.tsx`
- `app/app/student/constraints/page.tsx`
- `app/app/student/layout.tsx`
- `app/app/university/courses/page.tsx`
- `app/app/university/departments/page.tsx`
- `app/app/university/faculty/page.tsx`
- `app/app/university/insights/page.tsx`
- `app/app/university/layout.tsx`
- `app/app/university/members/page.tsx`
- `app/app/university/rooms/page.tsx`
- `app/app/university/sections/page.tsx`
- `app/app/university/students/page.tsx`
- `app/app/university/terms/page.tsx`
- `app/app/university/timetables/[id]/page.tsx`
- `app/app/university/timetables/page.tsx`
- `app/components/assistant/SyncShiftAssistant.tsx`
- `app/components/calendar/BlockModal.tsx`
- `app/components/calendar/CalendarHeader.tsx`
- `app/components/calendar/CalendarSkeleton.tsx`
- `app/components/calendar/ImportModal.tsx`
- `app/components/calendar/WeekView.tsx`
- `app/components/planner/AddTaskModal.tsx`
- `app/components/planner/PlanOptionsModal.tsx`
- `app/components/planner/PlanPreviewModal.tsx`
- `app/components/planner/WeeklyPlanHero.tsx`
- `app/components/ui/DatePicker.tsx`
- `app/components/ui/viewport.css`
- `app/components/ui/ViewportMetrics.tsx`
- `app/components/unified/AdminArea.tsx`
- `app/components/unified/ClassDetail.tsx`
- `app/components/unified/SubjectDetails.tsx`
- `app/components/unified/workspace.css`
