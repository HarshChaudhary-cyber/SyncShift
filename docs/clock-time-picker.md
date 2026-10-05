# Clock time picker verification

Date: 2026-10-05

Replaced the shared half-hour slot list with a clock face for choosing hours and minutes, AM/PM controls, and exact 24-hour text entry. The shared control is used by calendar events, the alternate block form, planner session previews, and settings quiet hours. Date selection still uses the existing calendar.

The popup is rendered outside scrolling form containers and bounded to the visual viewport, with internal vertical scrolling on short screens. Controls have accessible labels, keyboard focus stays in the popup, Escape cancels, and closing restores focus. Selecting an hour moves focus to the minute control. The control retains disabled/error states and supports named form values and min/max limits.

## Checks

- Local Docker production build: passed, including TypeScript.
- Frontend lint: zero errors, 179 existing warnings. Changed TimePicker component: no lint findings.
- Browser: clock selection 1:45 PM applied as 13:45; 12:00 AM applied as 00:00; exact entry accepted 23:59; 25:70 showed validation; Escape preserved the saved field value; date field opened its calendar.
- Keyboard: Enter selected an hour and focus moved to Select minute.
- Dark-mode browser measurements: 360, 390, 1366 CSS pixels wide, 800 high; zero document horizontal overflow, popup inside viewport, zero popup horizontal overflow.
- Short viewport: 360 by 400; popup remained inside viewport with internal vertical scrolling, and Set time remained reachable and applied the value.
- Screenshots and measurements are in screenshots/time-picker/.
- Test event was cancelled; no schedule records were saved.

Limits: a real phone software keyboard was not tested; the short viewport simulates reduced available height. This pass exercised the shared control in the calendar event form, not every consuming page or role. Range constraints have no active callers and were not browser-tested. Light mode was not separately checked in this pass.
