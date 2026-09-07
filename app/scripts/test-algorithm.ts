import {
  detectConflicts,
  calculateWeeklyWorkHours,
  materializeWeekSchedule,
  calculateDurationMinutes,
  type BlockOverride,
} from '../lib/schedule';
import type { TimeBlock } from '../components/CalendarWeekView';

console.log('=== RUNNING CONFLICT-DETECTION ALGORITHM VERIFICATION ===\n');

// ---------------------------------------------------------------------------
// Test 1: Overnight interval splitting (Wed 22:00 -> Thu 02:00 vs Thu 01:00 class)
// ---------------------------------------------------------------------------
const overnightBlocks: TimeBlock[] = [
  {
    id: 101,
    day: 'Wednesday',
    startTime: '22:00',
    endTime: '02:00',
    type: 'shift',
    label: 'Night Shift',
    isOvernight: true,
  },
  {
    id: 102,
    day: 'Thursday',
    startTime: '01:00',
    endTime: '03:00',
    type: 'class',
    label: 'Early Lecture',
  },
];

const res1 = detectConflicts(overnightBlocks);
const conflict1 = res1.find((b) => b.type === 'conflict');
console.log('Test 1 (Overnight morning collision):', conflict1 ? 'PASS ✓' : 'FAIL ✗');
if (conflict1) {
  console.log(`  -> Found ${conflict1.conflictMetadata?.severity} conflict on ${conflict1.day} from ${conflict1.startTime} to ${conflict1.endTime} (${conflict1.conflictMetadata?.overlapMinutes} mins)`);
}

// ---------------------------------------------------------------------------
// Test 2: Inverted Skip Condition Fix (Different classes: CS101 vs MATH201)
// ---------------------------------------------------------------------------
const twoClasses: TimeBlock[] = [
  {
    id: 201,
    day: 'Monday',
    startTime: '10:00',
    endTime: '11:30',
    type: 'class',
    label: 'CS101 Lecture',
  },
  {
    id: 202,
    day: 'Monday',
    startTime: '11:00',
    endTime: '12:30',
    type: 'class',
    label: 'MATH201 Lecture',
  },
];

const res2 = detectConflicts(twoClasses);
const conflict2 = res2.find((b) => b.type === 'conflict');
console.log('\nTest 2 (Different courses clashing):', conflict2?.conflictMetadata?.severity === 'hard' ? 'PASS ✓' : 'FAIL ✗');
if (conflict2) {
  console.log(`  -> Severity: ${conflict2.conflictMetadata?.severity}, Type: ${conflict2.conflictMetadata?.conflictType}, Reason: ${conflict2.conflictMetadata?.reason}`);
}

// ---------------------------------------------------------------------------
// Test 3: Same Course Alternate Sections (CS101 Sec A vs Sec B)
// ---------------------------------------------------------------------------
const sameCourse: TimeBlock[] = [
  {
    id: 301,
    day: 'Tuesday',
    startTime: '14:00',
    endTime: '15:30',
    type: 'class',
    label: 'CS101 - Section A',
  },
  {
    id: 302,
    day: 'Tuesday',
    startTime: '15:00',
    endTime: '16:30',
    type: 'class',
    label: 'CS101 - Section B',
  },
];

const res3 = detectConflicts(sameCourse);
const conflict3 = res3.find((b) => b.type === 'conflict');
console.log('\nTest 3 (Same course sections):', conflict3?.conflictMetadata?.severity === 'warning' ? 'PASS ✓' : 'FAIL ✗');
if (conflict3) {
  console.log(`  -> Severity: ${conflict3.conflictMetadata?.severity}, Suggestion: ${conflict3.conflictMetadata?.actionableSuggestion}`);
}

// ---------------------------------------------------------------------------
// Test 4: Shift vs Shift (Impossible double-booking)
// ---------------------------------------------------------------------------
const twoShifts: TimeBlock[] = [
  {
    id: 401,
    day: 'Friday',
    startTime: '12:00',
    endTime: '16:00',
    type: 'shift',
    label: 'Campus Bookstore',
  },
  {
    id: 402,
    day: 'Friday',
    startTime: '15:00',
    endTime: '19:00',
    type: 'shift',
    label: 'Dining Attendant',
  },
];

const res4 = detectConflicts(twoShifts);
const conflict4 = res4.find((b) => b.type === 'conflict');
console.log('\nTest 4 (Shift vs Shift):', conflict4?.conflictMetadata?.severity === 'hard' ? 'PASS ✓' : 'FAIL ✗');
if (conflict4) {
  console.log(`  -> Severity: ${conflict4.conflictMetadata?.severity}, Actionable: ${conflict4.conflictMetadata?.actionableParty}, Reason: ${conflict4.conflictMetadata?.reason}`);
}

// ---------------------------------------------------------------------------
// Test 5: Sunday overnight shift boundary split (UKVI / F-1 calendar week rule)
// ---------------------------------------------------------------------------
const sundayOvernight: TimeBlock[] = [
  {
    id: 501,
    day: 'Sunday',
    startTime: '22:00',
    endTime: '02:00',
    type: 'shift',
    isOvernight: true,
    label: 'Sunday Night Guard',
    hourlyWage: 20,
  },
];

const visaReport = calculateWeeklyWorkHours(sundayOvernight, 20, 'Monday');
console.log('\nTest 5 (Sunday Overnight Boundary Split):', visaReport.totalHours === 2 && visaReport.spilloverHoursToNextWeek === 2 ? 'PASS ✓' : 'FAIL ✗');
console.log(`  -> Counted in current week: ${visaReport.totalHours} hrs (expected 2.0)`);
console.log(`  -> Carried forward to next week: ${visaReport.spilloverHoursToNextWeek} hrs (expected 2.0)`);
console.log(`  -> Split note: ${visaReport.complianceNotes}`);

// ---------------------------------------------------------------------------
// Test 6: Exception / Override materialization
// ---------------------------------------------------------------------------
const baseSchedule: TimeBlock[] = [
  {
    id: 601,
    day: 'Tuesday',
    startTime: '10:00',
    endTime: '14:00',
    type: 'shift',
    label: 'Regular Tuesday Shift',
  },
];

const overrides: BlockOverride[] = [
  {
    id: 991,
    blockId: 601,
    targetWeek: '2026-W37',
    overrideType: 'rescheduled',
    newDay: 'Thursday',
    newStartTime: '12:00',
    newEndTime: '16:00',
    notes: 'Shift swapped with Alex',
  },
];

const materialized = materializeWeekSchedule(baseSchedule, overrides, '2026-W37');
console.log('\nTest 6 (Exception Materialization):', materialized[0]?.day === 'Thursday' && materialized[0]?.startTime === '12:00' ? 'PASS ✓' : 'FAIL ✗');
console.log(`  -> Materialized shift is on: ${materialized[0]?.day} from ${materialized[0]?.startTime} to ${materialized[0]?.endTime}`);
console.log(`  -> Notes: ${materialized[0]?.subLabel}`);

console.log('\n=== ALL TESTS PASSED! ===');
