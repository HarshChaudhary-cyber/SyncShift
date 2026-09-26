# Assistant capabilities

Open the assistant at http://localhost:3000 using the floating button or Ask SyncShift AI.

## App guidance and account data

Try “How do I use this app?”, “How do I import a timetable?”, “How does Smart Planner
work?”, “What classes do I have today?”, or “How many work hours do I have left?”.
The app guide is included in the model's context and works without an AI connection.
Account questions use authenticated server tools. Administrator tools retain their
institution and role checks. The assistant has supported app actions, not unrestricted
database or operating-system access.

## Automatic personal schedule action

“Move my today work to tomorrow” moves today's work occurrences at the same times.
It uses the user's timezone, checks overlaps and transition gaps, and checks the
next week's work limit when crossing a week boundary. If any destination is blocked,
none of the shifts move. Recurring shifts receive a one-time exception; next week's
schedule stays intact. Repeating the request after success makes no further changes.

Only this explicit date-scoped command currently executes without a confirmation
card. Other supported create, move, delete and university timetable actions continue
to use the existing previews. Ambiguous requests need clarification. Edit an occurrence
in Calendar to change it again.

## Attach timetable

The paperclip inside the assistant accepts:

| Format | Processing |
| --- | --- |
| ICS / ICAL | Calendar parser, preserving recurrence interval and effective dates |
| CSV / TXT | Local structured text parser; AI fallback when no entries are found |
| XLSX / XLS | Spreadsheet cells and common column headers; AI fallback for layouts |
| DOCX / PPTX | Document text/tables; AI fallback for layouts |
| DOC | Antiword conversion in the Docker image, then text parsing |
| PDF | AI parsing with local text/table/OCR fallback |
| JPG / JPEG / PNG / WebP | AI vision with local Tesseract OCR fallback |

Uploads are limited to 20 MB. Office archives are limited to 50 MB expanded; the
local PDF fallback handles at most 50 pages. Password-protected, corrupt, unreadable
or unsupported files produce an error rather than invented events. Legacy PPT must
be exported as PPTX or PDF. Not every file layout is guaranteed to parse completely.

“Automatically import clear entries” is enabled by default and can be unchecked.
Duplicates, conflicts, uncertain times and OCR results go to review. Check selected
entries before importing. Calendar → Import Timetable also allows inline correction.
Import dates use a consistent Monday-based preview and Sunday-based stored calendar.
Repeat submissions skip exact duplicates. Official classes cannot be edited through
personal shift commands.

## Runtime and verification

The Docker image installs openpyxl, xlrd, Antiword and Tesseract. After code changes:

```sh
docker compose build backend frontend
docker compose --env-file backend/.env up -d backend frontend
```

The environment-file option supplies the existing local Gemini key; Compose's explicit
database and Redis settings still point to the Docker services. Do not commit local
environment files. Open-ended AI and vision depend on that provider's availability
and quota. This release does not implement universal autonomous control of every app
feature. No emails or messages are sent by the new move/import actions.

Regression coverage includes occurrence-only moves, repeat requests, cross-user
isolation, all-or-nothing conflict handling, next-week work limits, spreadsheet and
Word extraction, import weekday conversion, duplicate submissions and invalid-batch
rollback. Use the sample CSV alongside the demo accounts for a manual upload check.
