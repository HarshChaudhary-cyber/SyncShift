# Scheduling control icon cleanup

2026-10-05 follow-up to the emoji remaining in the Add Class dialog.

Replaced decorative emoji with the existing Heroicons outline set in the calendar event and legacy block forms, recurrence choices, calendar hover/drag/today/summary views, import workflow, planner task/options/preview dialogs, planner page, and notification center. A shared `ScheduleIcon` component supplies consistently sized, decorative SVGs; adjacent labels remain accessible text. Recurrence buttons now expose their selected state with `aria-pressed`. Scheduling handlers, permissions, and stored user content were not changed.

Verified:

- Frontend lint: 0 errors, 179 warnings (same total as the previous change).
- Docker frontend production build, including TypeScript and route generation: passed.
- Rebuilt and recreated only the local frontend container.
- Reproduced the original dialog, then checked the updated class/shift switch and all three recurrence selections.
- At 360, 390, and 1366 CSS pixels: no document overflow and no emoji in the event form's rendered text.
- Opened the import and task dialogs; checked planner and notification text for remaining emoji in the exercised states. No imports, events, or tasks were submitted.

Evidence: [before](screenshots/scheduling-icons/before.jpg), [after desktop](screenshots/scheduling-icons/after-desktop.jpg), [after mobile](screenshots/scheduling-icons/after-mobile.jpg), [measurements](screenshots/scheduling-icons/checks.json).

This follow-up covers the scheduling and notification components listed above, not a claim that every legacy page or user-supplied text in the repository is emoji-free.
