'use client';

import React, { useMemo } from 'react';

export type BlockType = 'class' | 'shift' | 'conflict';

export interface TimeBlock {
  id?: string | number;
  day: string | number; // e.g. 'Monday', 'Mon', 'mon', or 0 (Sun) / 1 (Mon)
  startTime: string;    // "HH:MM" or "HH:MM:SS" (24h format, e.g. "09:30")
  endTime: string;      // "HH:MM" or "HH:MM:SS" (24h format, e.g. "11:00")
  type: BlockType;
  label: string;
  subLabel?: string;    // Optional: room, supervisor, notes, etc.
  courseCode?: string;
  repeatsWeekly?: boolean;
  isImported?: boolean;
  status?: string;
  durationMinutes?: number;
  isOvernight?: boolean;
  hourlyWage?: number;
  isRecurring?: boolean;
  specificDate?: string;
  conflictMetadata?: any;
  [key: string]: any;
}

export interface CalendarWeekViewProps {
  blocks?: TimeBlock[];
  startHour?: number;    // Earliest hour displayed (default: 7 -> 7:00 AM)
  endHour?: number;      // Latest hour displayed (default: 22 -> 10:00 PM)
  days?: string[];       // Days to display (default: Mon - Sun)
  onBlockClick?: (block: TimeBlock) => void;
  onBlockMove?: (blockId: string | number, newStartTime: string, newEndTime: string, newDay?: string) => void;
  onBlockResize?: (blockId: string | number, newEndTime: string) => void;
  className?: string;
  [key: string]: any;
}

const DEFAULT_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

/**
 * Normalizes day input (number, short name, full name) to full day name
 */
function normalizeDay(day: string | number | undefined | null): string {
  if (day === undefined || day === null) return 'Monday';
  if (typeof day === 'number') {
    // 0 = Sunday, 1 = Monday, ... 6 = Saturday (standard JS getDay order)
    const dayMap = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return dayMap[((day % 7) + 7) % 7] || 'Monday';
  }
  const clean = String(day).trim().toLowerCase();
  if (clean.startsWith('mon')) return 'Monday';
  if (clean.startsWith('tue')) return 'Tuesday';
  if (clean.startsWith('wed')) return 'Wednesday';
  if (clean.startsWith('thu')) return 'Thursday';
  if (clean.startsWith('fri')) return 'Friday';
  if (clean.startsWith('sat')) return 'Saturday';
  if (clean.startsWith('sun')) return 'Sunday';
  return String(day);
}

/**
 * Parses "HH:MM", "HH:MM:SS", or 12h "HH:MM AM/PM" to total minutes from midnight
 */
function parseTimeToMinutes(timeStr: string): number {
  if (!timeStr) return 0;
  const match = timeStr.trim().match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(am|pm)?$/i);
  if (match) {
    let hours = parseInt(match[1], 10) || 0;
    const minutes = parseInt(match[2], 10) || 0;
    const ampm = match[3]?.toLowerCase();
    if (ampm === 'pm' && hours < 12) hours += 12;
    if (ampm === 'am' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  }
  const [hStr, mStr] = timeStr.split(':');
  const hours = parseInt(hStr || '0', 10) || 0;
  const minutes = parseInt(mStr || '0', 10) || 0;
  return hours * 60 + minutes;
}

/**
 * Formats "09:30" or "09:30:00" to "9:30 AM"
 */
function formatTime12h(timeStr: string): string {
  if (!timeStr) return '';
  if (/\b(am|pm)\b/i.test(timeStr)) return timeStr;
  const parts = timeStr.split(':');
  const hours = parseInt(parts[0] || '0', 10) || 0;
  const minutes = parseInt(parts[1] || '0', 10) || 0;
  const period = hours >= 12 ? 'PM' : 'AM';
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  const paddedMin = String(minutes).padStart(2, '0');
  return `${hour12}:${paddedMin} ${period}`;
}

export const CalendarWeekView: React.FC<CalendarWeekViewProps> = ({
  blocks = [],
  startHour = 7,
  endHour = 22,
  days = DEFAULT_DAYS,
  onBlockClick,
  className = '',
}) => {
  const totalMinutesInView = Math.max(1, (endHour - startHour) * 60);
  const startMinute = startHour * 60;

  // Generate hour marks for the time gutter
  const hours = useMemo(() => {
    return Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);
  }, [startHour, endHour]);

  // Group and index blocks by normalized day
  const blocksByDay = useMemo(() => {
    const map = new Map<string, TimeBlock[]>();
    days.forEach((d) => map.set(d, []));

    blocks.forEach((block) => {
      const normalized = normalizeDay(block.day);
      if (map.has(normalized)) {
        map.get(normalized)!.push(block);
      }
    });

    return map;
  }, [blocks, days]);

  // Styling system per block type
  const getTypeStyles = (type: BlockType) => {
    switch (type) {
      case 'class':
        return {
          container:
            'bg-blue-50/90 text-blue-900 border-l-4 border-blue-600 shadow-sm hover:bg-blue-100 dark:bg-blue-950/70 dark:text-blue-100 dark:border-blue-400 dark:hover:bg-blue-900/80',
          badge: 'bg-blue-200/80 text-blue-800 dark:bg-blue-800 dark:text-blue-200',
          tag: 'Class',
          zIndex: 'z-10',
        };
      case 'shift':
        return {
          container:
            'bg-emerald-50/90 text-emerald-900 border-l-4 border-emerald-600 shadow-sm hover:bg-emerald-100 dark:bg-emerald-950/70 dark:text-emerald-100 dark:border-emerald-400 dark:hover:bg-emerald-900/80',
          badge: 'bg-emerald-200/80 text-emerald-800 dark:bg-emerald-800 dark:text-emerald-200',
          tag: 'Shift',
          zIndex: 'z-10',
        };
      case 'conflict':
        return {
          container:
            'bg-rose-100/95 text-rose-950 border-2 border-rose-600 ring-2 ring-rose-500/30 shadow-md hover:bg-rose-200 dark:bg-rose-950/90 dark:text-rose-100 dark:border-rose-400 dark:ring-rose-400/40 animate-pulse',
          badge: 'bg-rose-600 text-white font-bold tracking-wide uppercase',
          tag: '⚠️ Conflict',
          zIndex: 'z-20', // Ensure conflicts layer on top of colliding blocks
        };
      default:
        return {
          container: 'bg-zinc-100 text-zinc-800 border-l-4 border-zinc-400',
          badge: 'bg-zinc-200 text-zinc-700',
          tag: 'Event',
          zIndex: 'z-10',
        };
    }
  };

  return (
    <div
      className={`flex flex-col h-full select-none bg-white dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden ${className}`}
      style={{ '--cal-cols': `64px repeat(${days.length}, minmax(0, 1fr))` } as React.CSSProperties}
    >
      {/* Week Header */}
      <div
        className="grid border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 font-medium text-xs text-zinc-500 dark:text-zinc-400"
        style={{ gridTemplateColumns: `64px repeat(${days.length}, minmax(0, 1fr))` }}
      >
        <div className="p-3 text-center border-r border-zinc-200 dark:border-zinc-800">
          Time
        </div>
        {days.map((day) => (
          <div key={day} className="py-3 px-2 text-center border-r last:border-r-0 border-zinc-200 dark:border-zinc-800 font-semibold text-zinc-800 dark:text-zinc-200">
            <span className="hidden sm:inline">{day}</span>
            <span className="sm:hidden">{day.slice(0, 3)}</span>
          </div>
        ))}
      </div>

      {/* Calendar Grid Body */}
      <div className="relative flex-1 overflow-y-auto">
        <div
          className="grid relative"
          style={{
            gridTemplateColumns: `64px repeat(${days.length}, minmax(0, 1fr))`,
            minHeight: `${(endHour - startHour) * 64}px`,
          }}
        >
          {/* Time Gutter Column */}
          <div className="relative border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/40 dark:bg-zinc-900/20">
            {hours.map((hour, idx) => {
              const topPercent = ((idx * 60) / totalMinutesInView) * 100;
              const period = hour >= 12 ? 'PM' : 'AM';
              const displayHour = hour % 12 === 0 ? 12 : hour % 12;

              return (
                <div
                  key={hour}
                  className="absolute right-2 -translate-y-1/2 text-[11px] font-mono text-zinc-400 dark:text-zinc-500"
                  style={{ top: `${topPercent}%` }}
                >
                  {displayHour} {period}
                </div>
              );
            })}
          </div>

          {/* Day Columns */}
          {days.map((day) => {
            const dayBlocks = blocksByDay.get(day) || [];

            return (
              <div
                key={day}
                className="relative border-r last:border-r-0 border-zinc-200 dark:border-zinc-800 h-full group"
              >
                {/* Horizontal Grid Guidelines */}
                {hours.map((hour, idx) => {
                  const topPercent = ((idx * 60) / totalMinutesInView) * 100;
                  return (
                    <div
                      key={`grid-${hour}`}
                      className="absolute left-0 right-0 border-t border-zinc-100 dark:border-zinc-800/80 pointer-events-none"
                      style={{ top: `${topPercent}%` }}
                    />
                  );
                })}

                {/* Half-hour subtle guide */}
                {hours.slice(0, -1).map((hour, idx) => {
                  const topPercent = (((idx * 60) + 30) / totalMinutesInView) * 100;
                  return (
                    <div
                      key={`half-${hour}`}
                      className="absolute left-0 right-0 border-t border-dashed border-zinc-100/60 dark:border-zinc-800/40 pointer-events-none"
                      style={{ top: `${topPercent}%` }}
                    />
                  );
                })}

                {/* Render TimeBlocks */}
                {dayBlocks.map((block, index) => {
                  const startMin = parseTimeToMinutes(block.startTime);
                  const endMin = parseTimeToMinutes(block.endTime);

                  // Clamp positions to visible range
                  const clampedStart = Math.max(startMinute, startMin);
                  const clampedEnd = Math.min(startMinute + totalMinutesInView, endMin);
                  const duration = clampedEnd - clampedStart;

                  if (!duration || duration <= 0 || isNaN(duration)) return null;

                  const topPercent = ((clampedStart - startMinute) / totalMinutesInView) * 100;
                  const heightPercent = (duration / totalMinutesInView) * 100;

                  const styles = getTypeStyles(block.type);

                  return (
                    <div
                      key={block.id ?? `${day}-${index}`}
                      onClick={() => onBlockClick?.(block)}
                      style={{
                        top: `${topPercent}%`,
                        height: `${heightPercent}%`,
                      }}
                      className={`absolute left-1 right-1 rounded-md p-1.5 overflow-hidden transition-all duration-150 cursor-pointer flex flex-col justify-between ${styles.container} ${styles.zIndex}`}
                      title={`${block.label} (${formatTime12h(block.startTime)} - ${formatTime12h(block.endTime)})`}
                    >
                      <div className="flex flex-col min-h-0">
                        {/* Header: Label + Tag Badge */}
                        <div className="flex items-start justify-between gap-1">
                          <span className="font-semibold text-xs leading-tight line-clamp-1">
                            {block.label}
                          </span>
                          <span className={`text-[9px] px-1 py-0.5 rounded leading-none shrink-0 ${styles.badge}`}>
                            {styles.tag}
                          </span>
                        </div>

                        {/* Optional Sub-label (Room, notes, etc.) */}
                        {block.subLabel && (
                          <span className="text-[10px] opacity-80 line-clamp-1 mt-0.5">
                            {block.subLabel}
                          </span>
                        )}
                      </div>

                      {/* Time footer */}
                      <div className="text-[10px] font-mono font-medium opacity-90 mt-1">
                        {formatTime12h(block.startTime)} - {formatTime12h(block.endTime)}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CalendarWeekView;
