'use client';

import React, { useCallback, useMemo, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import DraggableBlock from './DraggableBlock';

// ---------------------------------------------------------------------------
// Types (re-exported so existing imports keep working)
// ---------------------------------------------------------------------------

export type BlockType = 'class' | 'shift' | 'conflict';
export type BlockStatus = 'enrolled' | 'tentative' | 'dropped';
export type ConflictSeverity = 'hard' | 'warning' | 'info';

export interface ConflictMetadata {
  severity: ConflictSeverity;
  conflictType: 'class_vs_class' | 'shift_vs_shift' | 'class_vs_shift' | 'section_alternative';
  overlapMinutes: number;
  reason: string;
  actionableParty?: 'shift' | 'class' | 'both';
  actionableSuggestion?: string;
  involvedBlockIds: (string | number)[];
}

export interface TimeBlock {
  /** Optional stable key for React reconciliation */
  id?: string | number;
  /**
   * Accepts full names ('Monday'), 3-letter abbreviations ('Mon'),
   * or standard JS day indices (0 = Sunday … 6 = Saturday).
   */
  day: string | number;
  /** 24-hour "HH:MM" or "HH:MM:SS", e.g. "09:30" */
  startTime: string;
  /** 24-hour "HH:MM" or "HH:MM:SS", e.g. "11:00" */
  endTime: string;
  type: BlockType;
  label: string;
  /** Course code for matching academic sections (e.g. CS101) */
  courseCode?: string;
  /** Optional secondary line: room number, supervisor name, notes, etc. */
  subLabel?: string;
  /** Whether this block repeats every week. Used for the cross-column confirm prompt. */
  repeatsWeekly?: boolean;
  /** Whether this block was imported from a timetable .ics file */
  isImported?: boolean;
  /** Status for what-if scenarios (default: 'enrolled') */
  status?: BlockStatus;
  /** Duration in minutes (especially useful for overnight shifts) */
  durationMinutes?: number;
  /** Whether this block crosses midnight into the next day */
  isOvernight?: boolean;
  /** Hourly wage ($/hr) for earnings calculations */
  hourlyWage?: number;
  /** Whether block is recurring vs single date */
  isRecurring?: boolean;
  /** Specific date for one-off blocks (YYYY-MM-DD) */
  specificDate?: string;
  /** Rich conflict categorization metadata */
  conflictMetadata?: ConflictMetadata;
  /** Sub-interval indicator for visual rendering of overnight shifts */
  isOvernightFragment?: 'start' | 'spillover';
  /** Original block ID when rendered as an overnight fragment */
  originalBlockId?: string | number;
  /** Whether the block is currently in-flight being saved via API */
  isSaving?: boolean;
}

export interface CalendarWeekViewProps {
  blocks: TimeBlock[];
  /** First visible hour (default 7 → 7 AM) */
  startHour?: number;
  /** Last visible hour (default 22 → 10 PM) */
  endHour?: number;
  /** Ordered list of day names to render (default: Mon–Sun) */
  days?: string[];
  onBlockClick?: (block: TimeBlock) => void;
  /**
   * Called when a block is dragged to a new time position or new day column.
   * `newDay` is only present when the block crossed to a different day.
   */
  onBlockMove?: (
    blockId: string | number,
    newStartTime: string,
    newEndTime: string,
    newDay?: string,
  ) => void;
  /** Called when a block is resized from the bottom edge */
  onBlockResize?: (blockId: string | number, newEndTime: string) => void;
  /** Snap increment in minutes (default 15) */
  snapMinutes?: number;
  className?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_DAYS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

/** Height in pixels allocated to each hour row */
const HOUR_HEIGHT_PX = 64;

// ---------------------------------------------------------------------------
// Pure helper functions
// ---------------------------------------------------------------------------

function normalizeDay(day: string | number): string {
  if (typeof day === 'number') {
    const map = [
      'Sunday', 'Monday', 'Tuesday', 'Wednesday',
      'Thursday', 'Friday', 'Saturday',
    ];
    return map[((day % 7) + 7) % 7] ?? 'Monday';
  }
  const c = day.trim().toLowerCase();
  if (c.startsWith('mon')) return 'Monday';
  if (c.startsWith('tue')) return 'Tuesday';
  if (c.startsWith('wed')) return 'Wednesday';
  if (c.startsWith('thu')) return 'Thursday';
  if (c.startsWith('fri')) return 'Friday';
  if (c.startsWith('sat')) return 'Saturday';
  if (c.startsWith('sun')) return 'Sunday';
  return day;
}

function getNextDay(day: string | number): string {
  const norm = normalizeDay(day);
  const idx = DEFAULT_DAYS.indexOf(norm);
  if (idx === -1) return norm;
  return DEFAULT_DAYS[(idx + 1) % DEFAULT_DAYS.length] ?? norm;
}

function timeToMinutes(timeStr: string): number {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  const h = parseInt(parts[0] ?? '0', 10) || 0;
  const m = parseInt(parts[1] ?? '0', 10) || 0;
  return h * 60 + m;
}

function minutesToTime(totalMinutes: number): string {
  const clamped = Math.max(0, Math.min(totalMinutes, 24 * 60));
  const h = Math.floor(clamped / 60);
  const min = clamped % 60;
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
}

function fmt12h(timeStr: string): string {
  if (!timeStr) return '';
  const parts = timeStr.split(':');
  const h = parseInt(parts[0] ?? '0', 10) || 0;
  const m = parseInt(parts[1] ?? '0', 10) || 0;
  const period = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${String(m).padStart(2, '0')} ${period}`;
}

function snapTo(value: number, step: number): number {
  return Math.round(value / step) * step;
}

// ---------------------------------------------------------------------------
// Style map
// ---------------------------------------------------------------------------

const TYPE_STYLES: Record<
  BlockType,
  { container: string; badge: string; tag: string; zIndex: string }
> = {
  class: {
    container:
      'bg-blue-50/90 text-blue-900 border-l-4 border-blue-600 shadow-sm ' +
      'hover:bg-blue-100 dark:bg-blue-950/70 dark:text-blue-100 ' +
      'dark:border-blue-400 dark:hover:bg-blue-900/80',
    badge: 'bg-blue-200/80 text-blue-800 dark:bg-blue-800 dark:text-blue-200',
    tag: 'Class',
    zIndex: 'z-10',
  },
  shift: {
    container:
      'bg-emerald-50/90 text-emerald-900 border-l-4 border-emerald-600 shadow-sm ' +
      'hover:bg-emerald-100 dark:bg-emerald-950/70 dark:text-emerald-100 ' +
      'dark:border-emerald-400 dark:hover:bg-emerald-900/80',
    badge: 'bg-emerald-200/80 text-emerald-800 dark:bg-emerald-800 dark:text-emerald-200',
    tag: 'Shift',
    zIndex: 'z-10',
  },
  conflict: {
    container:
      'bg-rose-100/95 text-rose-950 border-2 border-rose-600 ' +
      'ring-2 ring-rose-500/30 shadow-md hover:bg-rose-200 ' +
      'dark:bg-rose-950/90 dark:text-rose-100 dark:border-rose-400 ' +
      'dark:ring-rose-400/40 animate-pulse',
    badge: 'bg-rose-600 text-white font-bold tracking-wide uppercase',
    tag: '⚠ Conflict',
    zIndex: 'z-20',
  },
};

export const CONFLICT_STYLES: Record<
  ConflictSeverity,
  { container: string; badge: string; tag: string; zIndex: string }
> = {
  hard: {
    container:
      'bg-rose-100/95 text-rose-950 border-2 border-rose-600 ' +
      'ring-2 ring-rose-500/30 shadow-md hover:bg-rose-200 ' +
      'dark:bg-rose-950/90 dark:text-rose-100 dark:border-rose-400 ' +
      'dark:ring-rose-400/40 animate-pulse',
    badge: 'bg-rose-600 text-white font-bold tracking-wide uppercase',
    tag: '⛔ Hard Conflict',
    zIndex: 'z-20',
  },
  warning: {
    container:
      'bg-amber-100/95 text-amber-950 border-2 border-amber-500 ' +
      'ring-2 ring-amber-400/30 shadow-md hover:bg-amber-200 ' +
      'dark:bg-amber-950/90 dark:text-amber-100 dark:border-amber-400 ' +
      'dark:ring-amber-400/40',
    badge: 'bg-amber-600 text-white font-bold tracking-wide uppercase',
    tag: '⚠ Warning',
    zIndex: 'z-20',
  },
  info: {
    container:
      'bg-indigo-100/90 text-indigo-950 border-2 border-indigo-400 shadow-sm ' +
      'dark:bg-indigo-950/70 dark:text-indigo-100 dark:border-indigo-400',
    badge: 'bg-indigo-600 text-white font-bold tracking-wide uppercase',
    tag: 'ℹ Info',
    zIndex: 'z-20',
  },
};

export function getBlockStyles(block: TimeBlock) {
  if (block.type === 'conflict') {
    const sev = block.conflictMetadata?.severity ?? 'hard';
    return CONFLICT_STYLES[sev] ?? CONFLICT_STYLES.hard;
  }
  return TYPE_STYLES[block.type] ?? TYPE_STYLES.class;
}

// ---------------------------------------------------------------------------
// Y-only snap modifier (X is left free for cross-column movement)
// ---------------------------------------------------------------------------

function createYSnapModifier(gridSizePx: number) {
  return ({
    transform,
  }: {
    transform: { x: number; y: number; scaleX: number; scaleY: number };
  }) => ({
    ...transform,
    // X is intentionally left free — lets the block drift between columns
    y: Math.round(transform.y / gridSizePx) * gridSizePx,
  });
}

// ---------------------------------------------------------------------------
// DroppableDayColumn — thin wrapper so each column registers as a drop target
// ---------------------------------------------------------------------------

interface DroppableDayColumnProps {
  day: string;
  isOver: boolean;
  isDraggingAny: boolean;
  children: React.ReactNode;
  className?: string;
}

function DroppableDayColumn({
  day,
  isOver,
  isDraggingAny,
  children,
  className = '',
}: DroppableDayColumnProps) {
  const { setNodeRef } = useDroppable({ id: `col-${day}` });

  return (
    <div
      ref={setNodeRef}
      className={`relative border-r last:border-r-0 border-zinc-200 dark:border-zinc-800 transition-colors duration-150 ${
        isOver && isDraggingAny
          ? 'bg-indigo-50/60 dark:bg-indigo-950/25 ring-inset ring-1 ring-indigo-400/50 dark:ring-indigo-500/40'
          : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DragOverlay block — compact chip that follows the cursor across columns
// ---------------------------------------------------------------------------

interface OverlayBlockProps {
  block: TimeBlock;
}

function OverlayBlock({ block }: OverlayBlockProps) {
  const styles = TYPE_STYLES[block.type] ?? TYPE_STYLES.class;
  return (
    <div
      className={`rounded-md p-1.5 w-32 flex flex-col gap-0.5 shadow-xl ring-2 ring-black/10 dark:ring-white/10 cursor-grabbing scale-105 ${styles.container}`}
      style={{ opacity: 0.92 }}
    >
      <div className="flex items-start justify-between gap-1">
        <span className="font-semibold text-xs leading-tight line-clamp-2">
          {block.label}
        </span>
        <span className={`text-[9px] px-1 py-0.5 rounded leading-none shrink-0 ${styles.badge}`}>
          {styles.tag}
        </span>
      </div>
      <div className="text-[10px] font-mono opacity-80 mt-0.5">
        {fmt12h(block.startTime)} – {fmt12h(block.endTime)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const CalendarWeekView: React.FC<CalendarWeekViewProps> = ({
  blocks = [],
  startHour = 7,
  endHour = 22,
  days = DEFAULT_DAYS,
  onBlockClick,
  onBlockMove,
  onBlockResize,
  snapMinutes = 15,
  className = '',
}) => {
  const totalMinutes = (endHour - startHour) * 60;
  const startMinute = startHour * 60;

  const pxPerMinute = HOUR_HEIGHT_PX / 60;
  const minutesPerPixel = 1 / pxPerMinute;
  const snapPx = snapMinutes * pxPerMinute;

  // ── dnd-kit sensors & modifiers ─────────────────────────────────────────
  const pointerSensor = useSensor(PointerSensor, {
    activationConstraint: { distance: 5 },
  });
  const sensors = useSensors(pointerSensor);

  // Y-only snap — X is free for cross-column movement
  const snapModifier = useMemo(() => createYSnapModifier(snapPx), [snapPx]);
  const modifiers = useMemo(() => [snapModifier], [snapModifier]);

  // ── Drag state ──────────────────────────────────────────────────────────
  const [activeId, setActiveId] = useState<string | number | null>(null);
  const [activeBlock, setActiveBlock] = useState<TimeBlock | null>(null);
  // The day column the pointer is currently over (droppable id = "col-<Day>")
  const [overColId, setOverColId] = useState<string | null>(null);

  const hourMarks = useMemo<number[]>(
    () => Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i),
    [startHour, endHour],
  );

  const blocksByDay = useMemo(() => {
    const map = new Map<string, TimeBlock[]>();
    days.forEach((d) => map.set(d, []));

    blocks.forEach((block) => {
      const key = normalizeDay(block.day);
      const startM = timeToMinutes(block.startTime);
      const endM = timeToMinutes(block.endTime);
      const isOvernight = Boolean(block.isOvernight || endM < startM);

      if (!isOvernight) {
        map.get(key)?.push(block);
      } else {
        // Part 1: Evening fragment (startM -> 24:00)
        if (map.has(key)) {
          map.get(key)!.push({
            ...block,
            id: block.id != null ? `${block.id}-p1` : undefined,
            originalBlockId: block.id,
            endTime: '24:00',
            durationMinutes: 24 * 60 - startM,
            isOvernight: true,
            isOvernightFragment: 'start',
            subLabel: (block.subLabel ? `${block.subLabel} · ` : '') + '🌙 Evening',
          });
        }

        // Part 2: Morning fragment (00:00 -> endM on the next day)
        const nextDayKey = getNextDay(key);
        if (map.has(nextDayKey)) {
          map.get(nextDayKey)!.push({
            ...block,
            id: block.id != null ? `${block.id}-p2` : undefined,
            originalBlockId: block.id,
            day: nextDayKey,
            startTime: '00:00',
            durationMinutes: endM,
            isOvernight: true,
            isOvernightFragment: 'spillover',
            subLabel: (block.subLabel ? `${block.subLabel} · ` : '') + '🌙 Morning spillover',
          });
        }
      }
    });
    return map;
  }, [blocks, days]);

  const toTopPct = (minute: number) =>
    `${((minute - startMinute) / totalMinutes) * 100}%`;

  const toHeightPct = (durationMinutes: number) =>
    `${(durationMinutes / totalMinutes) * 100}%`;

  const gridCols = `64px repeat(${days.length}, minmax(0, 1fr))`;

  // ── Drag handlers ───────────────────────────────────────────────────────
  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
    const block = (event.active.data.current as { block: TimeBlock } | undefined)?.block;
    setActiveBlock(block ?? null);
    setOverColId(null);
  }, []);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    // event.over.id is "col-Monday", "col-Tuesday", etc.
    setOverColId(event.over ? String(event.over.id) : null);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null);
      setActiveBlock(null);

      const currentOverColId = overColId;
      setOverColId(null);

      const { active, delta } = event;
      if (!onBlockMove) return;

      const block = (active.data.current as { block: TimeBlock } | undefined)?.block;
      if (!block || (block.id == null && block.originalBlockId == null)) return;
      const effectiveId = block.originalBlockId ?? block.id!;

      // Determine target day from the droppable column id ("col-Monday" → "Monday")
      const targetDay = currentOverColId
        ? currentOverColId.replace(/^col-/, '')
        : null;

      const originDay = normalizeDay(block.day);
      const crossedColumn = targetDay !== null && targetDay !== originDay;

      // Compute new time from vertical delta
      const deltaMinutes = snapTo((delta?.y ?? 0) * minutesPerPixel, snapMinutes);
      const oldStart = timeToMinutes(block.startTime);
      const oldEnd = timeToMinutes(block.endTime);
      const isOvernight = Boolean(block.isOvernight || oldEnd < oldStart);
      const duration = block.durationMinutes ?? (isOvernight ? (24 * 60 - oldStart + oldEnd) : Math.max(0, oldEnd - oldStart));

      let newStart = oldStart + deltaMinutes;
      newStart = Math.max(startMinute, Math.min(newStart, startMinute + totalMinutes - duration));
      const newEnd = newStart + duration;

      // If neither time nor day changed, bail (avoids spurious state updates)
      if (deltaMinutes === 0 && !crossedColumn) return;

      onBlockMove(
        effectiveId,
        minutesToTime(newStart),
        minutesToTime(newEnd % (24 * 60)),
        crossedColumn ? targetDay : undefined,
      );
    },
    [overColId, onBlockMove, minutesPerPixel, snapMinutes, startMinute, totalMinutes],
  );

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setActiveBlock(null);
    setOverColId(null);
  }, []);

  // ── Resize handler ──────────────────────────────────────────────────────
  const handleResizeEnd = useCallback(
    (blockId: string | number, deltaMinutes: number) => {
      if (!onBlockResize) return;
      const block = blocks.find((b) => b.id === blockId || (b.id != null && String(blockId).startsWith(`${b.id}-`)));
      if (!block) return;
      const effectiveId = block.originalBlockId ?? block.id;
      if (effectiveId == null) return;

      const oldEnd = timeToMinutes(block.endTime);
      const oldStart = timeToMinutes(block.startTime);
      let newEnd = oldEnd + deltaMinutes;

      newEnd = Math.max(oldStart + snapMinutes, newEnd);
      newEnd = Math.min(startMinute + totalMinutes, newEnd);

      onBlockResize(effectiveId, minutesToTime(newEnd));
    },
    [blocks, onBlockResize, snapMinutes, startMinute, totalMinutes],
  );

  const handleBlockClickWrapper = useCallback(
    (b: TimeBlock) => {
      if (b.type === 'conflict') {
        onBlockClick?.(b);
        return;
      }
      const target =
        b.originalBlockId != null
          ? (blocks.find((x) => x.id === b.originalBlockId) ?? b)
          : b;
      onBlockClick?.(target);
    },
    [blocks, onBlockClick],
  );

  const isDraggingAny = activeId !== null;

  return (
    <DndContext
      sensors={sensors}
      modifiers={modifiers}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div
        className={`flex flex-col h-full bg-white dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden select-none ${className}`}
      >
        {/* ── Week Header ──────────────────────────────────────────────── */}
        <div
          className="grid border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-xs font-medium text-zinc-500 dark:text-zinc-400"
          style={{ gridTemplateColumns: gridCols }}
        >
          <div className="p-3 text-center border-r border-zinc-200 dark:border-zinc-800">
            Time
          </div>
          {days.map((day) => {
            const isColOver = overColId === `col-${day}` && isDraggingAny;
            return (
              <div
                key={day}
                className={`py-3 px-2 text-center border-r last:border-r-0 border-zinc-200 dark:border-zinc-800 font-semibold transition-colors duration-150 ${
                  isColOver
                    ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/25'
                    : 'text-zinc-800 dark:text-zinc-200'
                }`}
              >
                <span className="hidden sm:inline">{day}</span>
                <span className="sm:hidden">{day.slice(0, 3)}</span>
              </div>
            );
          })}
        </div>

        {/* ── Calendar Grid Body ───────────────────────────────────────── */}
        <div className="relative flex-1 overflow-y-auto">
          <div
            className="grid relative"
            style={{
              gridTemplateColumns: gridCols,
              minHeight: `${(endHour - startHour) * HOUR_HEIGHT_PX}px`,
            }}
          >
            {/* Time Gutter */}
            <div className="relative border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/40 dark:bg-zinc-900/20">
              {hourMarks.map((hour) => {
                const period = hour >= 12 ? 'PM' : 'AM';
                const display = hour % 12 === 0 ? 12 : hour % 12;
                return (
                  <div
                    key={hour}
                    className="absolute right-2 -translate-y-1/2 text-[11px] font-mono text-zinc-400 dark:text-zinc-500"
                    style={{ top: toTopPct(hour * 60) }}
                  >
                    {display} {period}
                  </div>
                );
              })}
            </div>

            {/* Day Columns — each is a droppable zone */}
            {days.map((day) => {
              const dayBlocks = blocksByDay.get(day) ?? [];
              const isColOver = overColId === `col-${day}`;

              return (
                <DroppableDayColumn
                  key={day}
                  day={day}
                  isOver={isColOver}
                  isDraggingAny={isDraggingAny}
                >
                  {/* Hour grid lines */}
                  {hourMarks.map((hour) => (
                    <div
                      key={`hr-${hour}`}
                      className="absolute left-0 right-0 border-t border-zinc-100 dark:border-zinc-800/80 pointer-events-none"
                      style={{ top: toTopPct(hour * 60) }}
                    />
                  ))}

                  {/* Half-hour dashed lines */}
                  {hourMarks.slice(0, -1).map((hour) => (
                    <div
                      key={`hh-${hour}`}
                      className="absolute left-0 right-0 border-t border-dashed border-zinc-100/70 dark:border-zinc-800/50 pointer-events-none"
                      style={{ top: toTopPct(hour * 60 + 30) }}
                    />
                  ))}

                  {/* TimeBlock chips */}
                  {dayBlocks.map((block) => {
                    const bStart = timeToMinutes(block.startTime);
                    const bEnd = timeToMinutes(block.endTime);

                    const visStart = Math.max(startMinute, bStart);
                    const visEnd = Math.min(startMinute + totalMinutes, bEnd);
                    const duration = visEnd - visStart;

                    if (duration <= 0) return null;

                    const blockStyles = getBlockStyles(block);

                    return (
                      <DraggableBlock
                        key={block.id ?? `${day}-${bStart}`}
                        block={block}
                        topPct={toTopPct(visStart)}
                        heightPct={toHeightPct(duration)}
                        styles={blockStyles}
                        activeId={activeId}
                        onBlockClick={handleBlockClickWrapper}
                        onResizeEnd={handleResizeEnd}
                        minutesPerPixel={minutesPerPixel}
                        snapMinutes={snapMinutes}
                        startLabel={fmt12h(block.startTime)}
                        endLabel={fmt12h(block.endTime)}
                      />
                    );
                  })}
                </DroppableDayColumn>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── DragOverlay — floating chip that follows the cursor ──────── */}
      <DragOverlay dropAnimation={null}>
        {activeBlock ? <OverlayBlock block={activeBlock} /> : null}
      </DragOverlay>
    </DndContext>
  );
};

export default CalendarWeekView;
