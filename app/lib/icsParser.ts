import type { TimeBlock } from '@/components/CalendarWeekView';
import { minutesToTime, timeToMinutes } from './schedule';

// ---------------------------------------------------------------------------
// Types & Data Model
// ---------------------------------------------------------------------------

export interface Section {
  id: string | number;
  courseCode?: string;
  courseName: string;
  room?: string;
  day: string; // 'Monday', 'Tuesday', ...
  startTime: string; // "HH:MM"
  endTime: string;   // "HH:MM"
  repeatsWeekly: boolean;
  isImported: true;
  source: 'import';
  rawUid?: string;
}

export interface ReviewItem {
  id: string;
  summary: string;
  reason: string;
  rawDateOrDetails?: string;
}

export interface ParseResult {
  sections: Section[];
  reviewItems: ReviewItem[];
  totalEventsFound: number;
}

const DAY_CODES: Record<string, string> = {
  MO: 'Monday',
  TU: 'Tuesday',
  WE: 'Wednesday',
  TH: 'Thursday',
  FR: 'Friday',
  SA: 'Saturday',
  SU: 'Sunday',
};

const DAY_NAMES = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Unescape RFC 5545 text sequences
 */
function unescapeIcsText(str: string): string {
  return str
    .replace(/\\n/gi, ' ')
    .replace(/\\,/g, ',')
    .replace(/\\;/g, ';')
    .replace(/\\\\/g, '\\')
    .trim();
}

/**
 * Parse an ISO duration string like "PT1H30M" or "PT50M" to total minutes
 */
function parseDurationToMinutes(durationStr: string): number | null {
  const match = durationStr.match(/P(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?/i);
  if (!match) return null;
  const hours = parseInt(match[1] ?? '0', 10) || 0;
  const mins = parseInt(match[2] ?? '0', 10) || 0;
  return hours * 60 + mins;
}

/**
 * Split SUMMARY into courseCode and courseName if possible.
 * e.g., "CS 210: Data Structures" -> code: "CS 210", name: "Data Structures"
 * e.g., "MATH 220 - Linear Algebra" -> code: "MATH 220", name: "Linear Algebra"
 */
function splitCourseTitle(summary: string): { courseCode?: string; courseName: string } {
  const matchColon = summary.match(/^([A-Z]{2,4}\s*\d{3}[A-Z]?)\s*[:–-]\s*(.+)$/i);
  if (matchColon && matchColon[1] && matchColon[2]) {
    return {
      courseCode: matchColon[1].trim(),
      courseName: matchColon[2].trim(),
    };
  }

  const matchSpace = summary.match(/^([A-Z]{2,4}\s*\d{3}[A-Z]?)\s+(.+)$/i);
  if (matchSpace && matchSpace[1] && matchSpace[2]) {
    return {
      courseCode: matchSpace[1].trim(),
      courseName: matchSpace[2].trim(),
    };
  }

  return { courseName: summary };
}

/**
 * Parses date-time property value like "20260901T093000Z" or "20260901T093000"
 */
function parseIcsDateTime(val: string): {
  isAllDay: boolean;
  dayName?: string;
  timeStr?: string;
  rawDate?: string;
} {
  const cleaned = val.trim();
  // Check if it's date-only: YYYYMMDD
  if (!cleaned.includes('T')) {
    return { isAllDay: true, rawDate: cleaned };
  }

  const match = cleaned.match(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
  if (!match) {
    return { isAllDay: false };
  }

  const [, year, month, day, hour, min] = match;
  if (!year || !month || !day || !hour || !min) {
    return { isAllDay: false };
  }

  const dateObj = new Date(
    parseInt(year, 10),
    parseInt(month, 10) - 1,
    parseInt(day, 10),
  );

  const dayIndex = dateObj.getDay();
  const dayName = DAY_NAMES[dayIndex] ?? 'Monday';
  const timeStr = `${hour}:${min}`;

  return {
    isAllDay: false,
    dayName,
    timeStr,
    rawDate: `${year}-${month}-${day}`,
  };
}

// ---------------------------------------------------------------------------
// Main Parser Function
// ---------------------------------------------------------------------------

/**
 * Parse an .ics file content into Sections and ReviewItems.
 * Conforms to RFC 5545 unfolding, RRULE multi-day recurrence, and
 * the "flag, don't silently drop" pattern for ambiguous events.
 */
export function parseIcsTimetable(icsContent: string): ParseResult {
  const sections: Section[] = [];
  const reviewItems: ReviewItem[] = [];

  if (!icsContent || !icsContent.includes('BEGIN:VCALENDAR')) {
    return {
      sections: [],
      reviewItems: [
        {
          id: 'invalid-file',
          summary: 'Invalid calendar file',
          reason: 'File does not contain a standard VCALENDAR header.',
        },
      ],
      totalEventsFound: 0,
    };
  }

  // RFC 5545 Line unfolding: CRLF or LF followed by a space or tab
  const unfolded = icsContent
    .replace(/\r\n[ \t]/g, '')
    .replace(/\n[ \t]/g, '')
    .replace(/\r/g, '');

  // Extract all VEVENT blocks
  const eventRegex = /BEGIN:VEVENT([\s\S]*?)END:VEVENT/gi;
  const rawEvents: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = eventRegex.exec(unfolded)) !== null) {
    if (match[1]) {
      rawEvents.push(match[1]);
    }
  }

  let eventCounter = 1;

  for (const rawEvent of rawEvents) {
    const lines = rawEvent.split('\n');
    let summary = '';
    let location = '';
    let dtstart = '';
    let dtend = '';
    let duration = '';
    let rrule = '';
    let uid = '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const colonIdx = trimmed.indexOf(':');
      if (colonIdx === -1) continue;

      const propHeader = trimmed.slice(0, colonIdx);
      const propVal = trimmed.slice(colonIdx + 1);
      const propName = propHeader.split(';')[0]?.toUpperCase().trim() ?? '';

      if (propName === 'SUMMARY') {
        summary = unescapeIcsText(propVal);
      } else if (propName === 'LOCATION') {
        location = unescapeIcsText(propVal);
      } else if (propName === 'DTSTART') {
        dtstart = propVal.trim();
      } else if (propName === 'DTEND') {
        dtend = propVal.trim();
      } else if (propName === 'DURATION') {
        duration = propVal.trim();
      } else if (propName === 'RRULE') {
        rrule = propVal.trim();
      } else if (propName === 'UID') {
        uid = propVal.trim();
      }
    }

    const itemSummary = summary || `Event #${eventCounter}`;

    // ── Flag: Missing Summary or Missing Start Time ──
    if (!summary) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: 'Untitled event',
        reason: 'Event is missing a title/SUMMARY property.',
      });
      continue;
    }

    if (!dtstart) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: itemSummary,
        reason: 'Missing start time (DTSTART).',
      });
      continue;
    }

    const startParsed = parseIcsDateTime(dtstart);

    // ── Flag: All-day event without specific timetable hours ──
    if (startParsed.isAllDay) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: itemSummary,
        reason: 'All-day event with no specific lecture hours.',
        rawDateOrDetails: startParsed.rawDate,
      });
      continue;
    }

    if (!startParsed.timeStr || !startParsed.dayName) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: itemSummary,
        reason: 'Could not parse start date or time format.',
        rawDateOrDetails: dtstart,
      });
      continue;
    }

    const startTime = startParsed.timeStr;
    let endTime = '';

    if (dtend) {
      const endParsed = parseIcsDateTime(dtend);
      if (endParsed.timeStr) {
        endTime = endParsed.timeStr;
      }
    } else if (duration) {
      const durMinutes = parseDurationToMinutes(duration);
      if (durMinutes != null && durMinutes > 0) {
        const startMins = timeToMinutes(startTime);
        endTime = minutesToTime(startMins + durMinutes);
      }
    }

    // ── Flag: Missing End Time or Invalid Duration ──
    if (!endTime) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: itemSummary,
        reason: 'Missing or unparseable end time (DTEND or DURATION).',
        rawDateOrDetails: `Start: ${startTime}`,
      });
      continue;
    }

    // ── Flag: End time is before or equal to start time ──
    if (timeToMinutes(endTime) <= timeToMinutes(startTime)) {
      reviewItems.push({
        id: `review-${eventCounter++}`,
        summary: itemSummary,
        reason: `Invalid time span (${startTime} – ${endTime}): end time is before or equal to start time.`,
      });
      continue;
    }

    // ── Recurrence & Days Inference from RRULE ──
    const { courseCode, courseName } = splitCourseTitle(summary);
    const targetDays: string[] = [];
    let repeatsWeekly = false;

    if (rrule) {
      const rruleParts = rrule.split(';').reduce<Record<string, string>>((acc, part) => {
        const [k, v] = part.split('=');
        if (k && v) acc[k.toUpperCase().trim()] = v.trim();
        return acc;
      }, {});

      if (rruleParts.FREQ?.toUpperCase() === 'WEEKLY') {
        repeatsWeekly = true;
        if (rruleParts.BYDAY) {
          // BYDAY can be "MO,WE,FR" or "TU,TH" or "1MO"
          const dayList = rruleParts.BYDAY.split(',');
          for (const rawCode of dayList) {
            // strip any integer prefixes like 1MO -> MO
            const cleanCode = rawCode.replace(/[^A-Z]/gi, '').toUpperCase();
            if (DAY_CODES[cleanCode]) {
              targetDays.push(DAY_CODES[cleanCode]);
            }
          }
        }
      }
    }

    // If no BYDAY was specified in RRULE, use the day from DTSTART
    if (targetDays.length === 0) {
      targetDays.push(startParsed.dayName);
    }

    // Create a Section for each recurring day
    for (const day of targetDays) {
      sections.push({
        id: `import-${eventCounter++}`,
        courseCode,
        courseName,
        room: location || undefined,
        day,
        startTime,
        endTime,
        repeatsWeekly,
        isImported: true,
        source: 'import',
        rawUid: uid || undefined,
      });
    }
  }

  return {
    sections,
    reviewItems,
    totalEventsFound: rawEvents.length,
  };
}

/**
 * Convert a Section entry into a TimeBlock for the calendar view
 */
export function sectionToTimeBlock(section: Section): TimeBlock {
  const displayLabel = section.courseCode
    ? `${section.courseCode}: ${section.courseName}`
    : section.courseName;

  return {
    id: section.id,
    day: section.day,
    startTime: section.startTime,
    endTime: section.endTime,
    type: 'class',
    label: displayLabel,
    subLabel: section.room,
    repeatsWeekly: section.repeatsWeekly,
    isImported: true,
  };
}
