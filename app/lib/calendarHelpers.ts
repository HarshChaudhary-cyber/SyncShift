/**
 * Helper utilities for calendar week calculations, day conversion, and conflict detection.
 */

export interface ConflictItem {
  id: number;
  block_a_id: number;
  block_b_id: number;
  overlap_minutes: number;
  severity: 'hard' | 'warning' | 'info' | string;
  overlap_start?: string;
  overlap_end?: string;
  day_of_week?: number | null;
  description?: string | null;
}

/**
 * Returns the Monday of the week for a given Date in "YYYY-MM-DD" format (ISO 8601).
 * If a Sunday is provided, returns the Monday of that same week (6 days prior).
 */
export function getMondayOfWeek(inputDate: Date | string = new Date()): string {
  const d = typeof inputDate === 'string' ? new Date(inputDate) : new Date(inputDate);
  const day = d.getDay(); // 0 = Sunday, 1 = Monday ... 6 = Saturday
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);

  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export const DAY_NAMES = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const;

export const DAY_MAP: Record<string, number> = {
  sunday: 0,
  monday: 1,
  tuesday: 2,
  wednesday: 3,
  thursday: 4,
  friday: 5,
  saturday: 6,
  sun: 0,
  mon: 1,
  tue: 2,
  wed: 3,
  thu: 4,
  fri: 5,
  sat: 6,
};

/**
 * Converts a day name (string) or number to a 0-6 day of week integer (0 = Sun, 1 = Mon ... 6 = Sat).
 */
export function dayToNumber(day: string | number): number {
  if (typeof day === 'number') {
    return ((day % 7) + 7) % 7;
  }
  const clean = day.trim().toLowerCase();
  return DAY_MAP[clean] ?? 1;
}

/**
 * Converts a 0-6 day index to its full day name ("Monday", "Tuesday", etc.).
 */
export function numberToDay(dayNum: number): string {
  const normalized = ((dayNum % 7) + 7) % 7;
  return DAY_NAMES[normalized] || 'Monday';
}

/**
 * Checks if a block participates in any active schedule conflict.
 */
export function isBlockInConflict(
  blockId: number | string,
  conflicts: ConflictItem[] = []
): boolean {
  const numericId = Number(blockId);
  return conflicts.some(
    (c) => c.block_a_id === numericId || c.block_b_id === numericId
  );
}

/**
 * Returns all conflict records that involve this block.
 */
export function getBlockConflicts(
  blockId: number | string,
  conflicts: ConflictItem[] = []
): ConflictItem[] {
  const numericId = Number(blockId);
  return conflicts.filter(
    (c) => c.block_a_id === numericId || c.block_b_id === numericId
  );
}
