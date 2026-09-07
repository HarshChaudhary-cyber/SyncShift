import type { TimeBlock, ConflictMetadata, ConflictSeverity } from '@/components/CalendarWeekView';

// ---------------------------------------------------------------------------
// Pure time helpers
// ---------------------------------------------------------------------------

export function timeToMinutes(t: string): number {
  if (!t) return 0;
  const parts = t.split(':');
  return (parseInt(parts[0] ?? '0', 10) || 0) * 60 + (parseInt(parts[1] ?? '0', 10) || 0);
}

export function minutesToTime(m: number): string {
  const clamped = Math.max(0, Math.min(m, 24 * 60));
  const h = Math.floor(clamped / 60);
  const min = clamped % 60;
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
}

/**
 * Calculates duration in minutes, handling overnight blocks crossing midnight
 */
export function calculateDurationMinutes(
  startTime: string,
  endTime: string,
  isOvernight?: boolean,
): number {
  const start = timeToMinutes(startTime);
  const end = timeToMinutes(endTime);
  if (isOvernight || end < start) {
    // e.g. 22:00 (1320) to 02:00 (120) -> (1440 - 1320) + 120 = 240 mins (4 hrs)
    return (24 * 60 - start) + end;
  }
  return Math.max(0, end - start);
}

// ---------------------------------------------------------------------------
// Single-Week Exception / Override Data Model & Resolver
// ---------------------------------------------------------------------------

export interface BlockOverride {
  id?: string | number;
  blockId: string | number;
  targetWeek: string; // e.g. "2026-W37" or specific week identifier
  overrideType: 'cancelled' | 'rescheduled' | 'custom';
  newDay?: string;
  newStartTime?: string;
  newEndTime?: string;
  newDurationMinutes?: number;
  notes?: string;
}

/**
 * Materializes the active schedule for a specific target week by overlaying
 * single-week exceptions (`block_overrides`) on top of base recurring `time_blocks`.
 * Must be executed BEFORE conflict detection and weekly hours calculations.
 */
export function materializeWeekSchedule(
  blocks: TimeBlock[],
  overrides: BlockOverride[] = [],
  targetWeek?: string,
): TimeBlock[] {
  if (!overrides.length || !targetWeek) return blocks;

  const relevantOverrides = new Map<string | number, BlockOverride>();
  for (const ov of overrides) {
    if (ov.targetWeek === targetWeek) {
      relevantOverrides.set(ov.blockId, ov);
    }
  }

  const materialized: TimeBlock[] = [];

  for (const block of blocks) {
    if (block.id == null || !relevantOverrides.has(block.id)) {
      materialized.push(block);
      continue;
    }

    const ov = relevantOverrides.get(block.id)!;
    if (ov.overrideType === 'cancelled') {
      // Exclude cancelled occurrence this week (e.g. sick day, holiday)
      continue;
    }

    if (ov.overrideType === 'rescheduled') {
      const newDay = ov.newDay ?? block.day;
      const newStart = ov.newStartTime ?? block.startTime;
      const newEnd = ov.newEndTime ?? block.endTime;
      const isOvernight = ov.newEndTime && ov.newStartTime ? ov.newEndTime < ov.newStartTime : block.isOvernight;
      const duration = calculateDurationMinutes(newStart, newEnd, isOvernight);

      materialized.push({
        ...block,
        day: newDay,
        startTime: newStart,
        endTime: newEnd,
        isOvernight,
        durationMinutes: duration,
        subLabel: (ov.notes ? `${ov.notes} · ` : '') + '(Rescheduled for this week)',
      });
    } else {
      materialized.push(block);
    }
  }

  return materialized;
}

// ---------------------------------------------------------------------------
// Visa-hour compliance & Earnings calculator (with Sunday midnight week-split)
// ---------------------------------------------------------------------------

export interface VisaComplianceReport {
  totalHours: number;
  totalEarnings: number;
  limitHours: number;
  remainingHours: number;
  isViolation: boolean;
  shiftCount: number;
  hasSplitOvernight: boolean;
  spilloverHoursToNextWeek: number;
  complianceNotes?: string;
}

const NORM_DAY_MAP: Record<string, string> = {
  '0': 'Sunday',
  '1': 'Monday',
  '2': 'Tuesday',
  '3': 'Wednesday',
  '4': 'Thursday',
  '5': 'Friday',
  '6': 'Saturday',
  sun: 'Sunday',
  sunday: 'Sunday',
  mon: 'Monday',
  monday: 'Monday',
  tue: 'Tuesday',
  tuesday: 'Tuesday',
  wed: 'Wednesday',
  wednesday: 'Wednesday',
  thu: 'Thursday',
  thursday: 'Thursday',
  fri: 'Friday',
  friday: 'Friday',
  sat: 'Saturday',
  saturday: 'Saturday',
};

function normalizeDay(d: string | number): string {
  const s = String(d).toLowerCase().trim();
  return NORM_DAY_MAP[s] ?? String(d);
}

/**
 * Calculates total weekly shift hours committed by a student and evaluates
 * against their visa legal work limit (e.g. 20 hrs/week for UK Tier 4/Student Route or US F-1).
 *
 * CRITICAL VISA RULE:
 * UKVI defines the working week as Monday 00:00 to Sunday 23:59.
 * US DOL/F-1 payroll audits enforce calendar week boundaries.
 * An overnight shift starting Sunday at 22:00 and ending Monday at 02:00 crosses the
 * week boundary:
 *  - 2 hours (22:00 -> 24:00 Sunday) belong to THIS week.
 *  - 2 hours (00:00 -> 02:00 Monday) belong to NEXT week.
 * Naively counting all 4 hours in this week causes false visa violations!
 */
export function calculateWeeklyWorkHours(
  blocks: TimeBlock[],
  limitHours: number = 20,
  weekStartDay: 'Monday' | 'Sunday' = 'Monday',
): VisaComplianceReport {
  let totalMinutes = 0;
  let totalEarnings = 0;
  let shiftCount = 0;
  let hasSplitOvernight = false;
  let spilloverHoursToNextWeek = 0;

  // The last day of the calendar week:
  // If week starts Monday, last day is Sunday.
  // If week starts Sunday, last day is Saturday.
  const lastDayOfWeek = weekStartDay === 'Monday' ? 'Sunday' : 'Saturday';

  for (const block of blocks) {
    if (block.type !== 'shift') continue;
    if (block.status === 'dropped') continue;

    const blockDay = normalizeDay(block.day);
    const startM = timeToMinutes(block.startTime);
    const endM = timeToMinutes(block.endTime);
    const isOvernight = Boolean(block.isOvernight || endM < startM);
    const totalDuration = block.durationMinutes ?? calculateDurationMinutes(block.startTime, block.endTime, isOvernight);

    shiftCount++;

    // Check if shift is on the boundary day and crosses midnight into the next week
    if (blockDay === lastDayOfWeek && isOvernight) {
      // Pre-midnight portion (counted in this week)
      const thisWeekMins = 24 * 60 - startM;
      // Post-midnight portion (spills over into next calendar week)
      const nextWeekMins = endM;

      totalMinutes += thisWeekMins;
      hasSplitOvernight = true;
      spilloverHoursToNextWeek += Math.round((nextWeekMins / 60) * 10) / 10;

      if (block.hourlyWage && block.hourlyWage > 0) {
        totalEarnings += (thisWeekMins / 60) * block.hourlyWage;
      }
    } else {
      // Shift is completely within this calendar week (or midweek overnight like Wed->Thu)
      totalMinutes += totalDuration;

      if (block.hourlyWage && block.hourlyWage > 0) {
        totalEarnings += (totalDuration / 60) * block.hourlyWage;
      }
    }
  }

  const totalHours = Math.round((totalMinutes / 60) * 10) / 10;
  const remainingHours = Math.max(0, Math.round((limitHours - totalHours) * 10) / 10);
  const isViolation = totalHours > limitHours;

  let complianceNotes: string | undefined;
  if (hasSplitOvernight) {
    complianceNotes = `Sunday overnight shift split at 24:00 boundary: ${spilloverHoursToNextWeek}h carries forward to next week (UKVI/F-1 calendar week rule).`;
  }

  return {
    totalHours,
    totalEarnings: Math.round(totalEarnings * 100) / 100,
    limitHours,
    remainingHours,
    isViolation,
    shiftCount,
    hasSplitOvernight,
    spilloverHoursToNextWeek,
    complianceNotes,
  };
}

// ---------------------------------------------------------------------------
// Conflict detection — sweep-line algorithm supporting What-If & Overnight
// ---------------------------------------------------------------------------

const DAY_ORDER = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

export function getNextDay(day: string): string {
  const norm = normalizeDay(day);
  const idx = DAY_ORDER.indexOf(norm);
  if (idx === -1) return norm;
  return DAY_ORDER[(idx + 1) % DAY_ORDER.length] ?? norm;
}

/**
 * Extracts a normalized course code or identifier from a block.
 * Matches patterns like "CS 210", "MATH-220", "PHYS 150", "CS101"
 */
export function extractCourseCode(block: TimeBlock): string {
  if (block.courseCode) return block.courseCode.trim().toUpperCase();
  const label = block.label.trim();
  const match = label.match(/^([A-Z]{2,5}\s*[-]?\s*\d{3,4}[A-Z]?)/i);
  if (match) return match[1].replace(/[\s-]+/g, '').toUpperCase();
  return label.split(':')[0]?.trim().toUpperCase() ?? label.toUpperCase();
}

interface ExpandedInterval {
  sourceBlock: TimeBlock;
  day: string;
  startMinutes: number;
  endMinutes: number;
  isOvernightPart?: 'start' | 'spillover';
}

/**
 * Given an array of class/shift blocks, computes auto-generated conflict blocks
 * for any overlapping pairs on the same day.
 *
 * GAPS & GOTCHAS RESOLVED:
 * 1. Overnight interval splitting: Blocks crossing midnight are split into [start -> 1440]
 *    and [0 -> end] on next day so standard overlap testing and next-day morning classes
 *    are accurately compared without 24-hr clock inversion bugs.
 * 2. Course-skipping logic: Does NOT skip different courses! Different classes clashing
 *    (CS101 vs MATH201) are flagged as HARD conflicts. Same course different sections
 *    (CS101 Sec A vs Sec B) are flagged as WARNING / selection alternatives.
 * 3. Severity model:
 *    - class vs class (different courses) -> HARD
 *    - shift vs shift -> HARD (physically impossible double-booking)
 *    - class vs shift -> HARD (class mandatory for visa/degree; shift flagged as flexible)
 *    - same course section alternatives -> WARNING
 *    - tentative / what-if blocks -> WARNING (sandbox preview)
 */
export function detectConflicts(blocks: TimeBlock[]): TimeBlock[] {
  // 1. Expand blocks into day-intervals (handling overnight spillover into next day)
  const intervalsByDay = new Map<string, ExpandedInterval[]>();

  for (const block of blocks) {
    if (block.type === 'conflict') continue;
    if (block.status === 'dropped') continue;

    const day = normalizeDay(block.day);
    const startM = timeToMinutes(block.startTime);
    const endM = timeToMinutes(block.endTime);
    const isOvernight = Boolean(block.isOvernight || endM < startM);

    if (!intervalsByDay.has(day)) intervalsByDay.set(day, []);

    if (!isOvernight) {
      intervalsByDay.get(day)!.push({
        sourceBlock: block,
        day,
        startMinutes: startM,
        endMinutes: endM,
      });
    } else {
      // Day 1 portion: startM -> 24:00 (1440 mins)
      intervalsByDay.get(day)!.push({
        sourceBlock: block,
        day,
        startMinutes: startM,
        endMinutes: 24 * 60,
        isOvernightPart: 'start',
      });

      // Day 2 portion: 00:00 -> endM on the next day
      const nextDay = getNextDay(day);
      if (!intervalsByDay.has(nextDay)) intervalsByDay.set(nextDay, []);
      intervalsByDay.get(nextDay)!.push({
        sourceBlock: block,
        day: nextDay,
        startMinutes: 0,
        endMinutes: endM,
        isOvernightPart: 'spillover',
      });
    }
  }

  const conflicts: TimeBlock[] = [];
  let conflictId = 9000;

  // Track conflict pairs to avoid duplicate conflict chips on identical intervals
  const seenPairKeys = new Set<string>();

  for (const [day, intervals] of intervalsByDay) {
    const sorted = [...intervals].sort((a, b) => a.startMinutes - b.startMinutes);

    for (let i = 0; i < sorted.length; i++) {
      for (let j = i + 1; j < sorted.length; j++) {
        const a = sorted[i]!;
        const b = sorted[j]!;

        // Don't compare a block with itself (e.g. overnight fragments of the same block)
        if (
          a.sourceBlock.id != null &&
          b.sourceBlock.id != null &&
          a.sourceBlock.id === b.sourceBlock.id
        ) {
          continue;
        }

        // What-if logic: two tentative blocks do NOT conflict with each other
        if (
          a.sourceBlock.status === 'tentative' &&
          b.sourceBlock.status === 'tentative'
        ) {
          continue;
        }

        // Sweep-line termination for sorted intervals
        if (a.endMinutes <= b.startMinutes) continue;

        // Calculate overlap boundaries
        const overlapStart = Math.max(a.startMinutes, b.startMinutes);
        const overlapEnd = Math.min(a.endMinutes, b.endMinutes);
        const overlapMinutes = overlapEnd - overlapStart;

        if (overlapMinutes <= 0) continue;

        // Deduplication key per day
        const aId = a.sourceBlock.id ?? a.sourceBlock.label;
        const bId = b.sourceBlock.id ?? b.sourceBlock.label;
        const pairKey = `${day}-${Math.min(Number(aId) || 0, Number(bId) || 0)}-${Math.max(Number(aId) || 0, Number(bId) || 0)}-${overlapStart}-${overlapEnd}`;
        if (seenPairKeys.has(pairKey)) continue;
        seenPairKeys.add(pairKey);

        const aTitle = a.sourceBlock.label.split(':')[0] ?? a.sourceBlock.label;
        const bTitle = b.sourceBlock.label.split(':')[0] ?? b.sourceBlock.label;

        const isWhatIf =
          a.sourceBlock.status === 'tentative' ||
          b.sourceBlock.status === 'tentative';

        // -------------------------------------------------------------------
        // Severity & Metadata Categorization
        // -------------------------------------------------------------------
        let severity: ConflictSeverity = 'hard';
        let conflictType: ConflictMetadata['conflictType'] = 'class_vs_shift';
        let actionableParty: ConflictMetadata['actionableParty'] = undefined;
        let reason = '';
        let actionableSuggestion = '';

        if (a.sourceBlock.type === 'class' && b.sourceBlock.type === 'class') {
          const aCourse = extractCourseCode(a.sourceBlock);
          const bCourse = extractCourseCode(b.sourceBlock);

          if (aCourse && bCourse && aCourse === bCourse) {
            // Same course alternate sections (e.g. CS101 Lecture A vs CS101 Lecture B)
            severity = 'warning';
            conflictType = 'section_alternative';
            reason = `Same course (${aCourse}) alternate section conflict`;
            actionableSuggestion = 'Select one section to enroll in';
          } else {
            // Two different classes clashing
            severity = 'hard';
            conflictType = 'class_vs_class';
            actionableParty = 'class';
            reason = 'Simultaneous academic lectures: impossible to attend both';
            actionableSuggestion = 'Class attendance mandatory for visa/degree. Switch section with advisor.';
          }
        } else if (a.sourceBlock.type === 'shift' && b.sourceBlock.type === 'shift') {
          // Two work shifts overlapping
          severity = 'hard';
          conflictType = 'shift_vs_shift';
          actionableParty = 'both';
          reason = 'Double-booked work shifts: physically impossible to work both';
          actionableSuggestion = 'Drop or swap one shift with a coworker to avoid visa/payroll audit.';
        } else {
          // Class vs Shift overlap
          severity = 'hard';
          conflictType = 'class_vs_shift';
          actionableParty = 'shift';
          const shiftBlock = a.sourceBlock.type === 'shift' ? a.sourceBlock : b.sourceBlock;
          reason = 'Academic class overlaps work shift';
          actionableSuggestion = `Class takes legal priority. Request shift swap/adjustment for "${shiftBlock.label}".`;
        }

        // What-If downgrade
        if (isWhatIf) {
          severity = 'warning';
          reason += ' (What-If Preview)';
        }

        const overlapLabel =
          overlapMinutes >= 60
            ? overlapMinutes % 60 === 0
              ? `${overlapMinutes / 60}h overlap`
              : `${Math.floor(overlapMinutes / 60)}h ${overlapMinutes % 60}m overlap`
            : `${overlapMinutes}m overlap`;

        const conflictMetadata: ConflictMetadata = {
          severity,
          conflictType,
          overlapMinutes,
          reason,
          actionableParty,
          actionableSuggestion,
          involvedBlockIds: [a.sourceBlock.id ?? 0, b.sourceBlock.id ?? 0],
        };

        conflicts.push({
          id: conflictId++,
          day,
          startTime: minutesToTime(overlapStart),
          endTime: minutesToTime(overlapEnd),
          type: 'conflict',
          label: `${aTitle} ↔ ${bTitle}`,
          subLabel: isWhatIf ? `${overlapLabel} (What-If Preview)` : overlapLabel,
          status: isWhatIf ? 'tentative' : 'enrolled',
          conflictMetadata,
        });
      }
    }
  }

  return [...blocks, ...conflicts];
}

/**
 * Checks whether a candidate block overlaps any existing blocks (handling overnight).
 * Used by the form to show an instant pre-submit warning.
 */
export function findConflictsFor(
  candidate: TimeBlock,
  existingBlocks: TimeBlock[],
): TimeBlock[] {
  const candidateDay = normalizeDay(candidate.day);
  const candStart = timeToMinutes(candidate.startTime);
  const candEnd = timeToMinutes(candidate.endTime);
  const candOvernight = Boolean(candidate.isOvernight || candEnd < candStart);

  // Candidate intervals
  const candIntervals: { day: string; start: number; end: number }[] = [];
  if (!candOvernight) {
    candIntervals.push({ day: candidateDay, start: candStart, end: candEnd });
  } else {
    candIntervals.push({ day: candidateDay, start: candStart, end: 24 * 60 });
    candIntervals.push({ day: getNextDay(candidateDay), start: 0, end: candEnd });
  }

  return existingBlocks.filter((b) => {
    if (b.type === 'conflict') return false;
    if (b.status === 'dropped') return false;
    if (b.id != null && b.id === candidate.id) return false;

    // Both tentative don't conflict
    if (candidate.status === 'tentative' && b.status === 'tentative') return false;

    const bDay = normalizeDay(b.day);
    const bStart = timeToMinutes(b.startTime);
    const bEnd = timeToMinutes(b.endTime);
    const bOvernight = Boolean(b.isOvernight || bEnd < bStart);

    const bIntervals: { day: string; start: number; end: number }[] = [];
    if (!bOvernight) {
      bIntervals.push({ day: bDay, start: bStart, end: bEnd });
    } else {
      bIntervals.push({ day: bDay, start: bStart, end: 24 * 60 });
      bIntervals.push({ day: getNextDay(bDay), start: 0, end: bEnd });
    }

    // Check if any interval intersects
    for (const cInt of candIntervals) {
      for (const bInt of bIntervals) {
        if (cInt.day === bInt.day) {
          if (cInt.start < bInt.end && bInt.start < cInt.end) {
            return true;
          }
        }
      }
    }

    return false;
  });
}
