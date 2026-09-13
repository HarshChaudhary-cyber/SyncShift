'use client';

import React, { useState } from 'react';
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
} from '@dnd-kit/core';
import { addDays, parseISO, format } from 'date-fns';
import { useCalendar } from '@/context/CalendarContext';
import { useAuthContext } from '@/context/AuthContext';
import { BlockOut } from '@/lib/api';
import DayColumn from './DayColumn';
import TimeGutter from './TimeGutter';
import ClientOnlyDnd from '@/components/ClientOnlyDnd';

interface WeekViewProps {
  onBlockClick: (block: BlockOut) => void;
  onSlotClick?: (dayIndex: number, startTime: string, endTime: string) => void;
  onReplanStudy?: (taskId: number) => Promise<void> | void;
}

const START_HOUR = 6;
const END_HOUR = 22;
const HOUR_HEIGHT = 60;

const ALL_DAYS = [
  { index: 1, name: 'Monday', short: 'Mon' },
  { index: 2, name: 'Tuesday', short: 'Tue' },
  { index: 3, name: 'Wednesday', short: 'Wed' },
  { index: 4, name: 'Thursday', short: 'Thu' },
  { index: 5, name: 'Friday', short: 'Fri' },
  { index: 6, name: 'Saturday', short: 'Sat' },
  { index: 0, name: 'Sunday', short: 'Sun' },
];

/**
 * Returns today's YYYY-MM-DD in the user's timezone.
 */
function getTodayDateStr(timeZone: string): string {
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
    return formatter.format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

export default function WeekView({ onBlockClick, onSlotClick, onReplanStudy }: WeekViewProps) {
  const { blocks, conflicts, weekStart, moveBlock, resizeBlock, deleteBlock, viewMode } =
    useCalendar();
  const { user } = useAuthContext();
  const timezone =
    user?.timezone ||
    (typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'UTC');

  const [activeDragBlock, setActiveDragBlock] = useState<BlockOut | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  );

  const parseMinutes = (t: string) => {
    const p = t.split(':');
    return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
  };

  const toTimeString = (m: number) => {
    const h = Math.floor(m / 60);
    const min = m % 60;
    return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveDragBlock(null);
    const { active, over, delta } = event;
    if (!active?.data?.current?.block) return;

    const block = active.data.current.block as BlockOut;
    const targetDayIndex =
      over?.data?.current?.dayIndex !== undefined
        ? over.data.current.dayIndex
        : block.day_of_week;

    const origStart = parseMinutes(block.start_time);
    const origEnd = parseMinutes(block.end_time);
    const duration = origEnd - origStart;

    const deltaMinutes = Math.round(((delta.y / HOUR_HEIGHT) * 60) / 15) * 15;
    const minAllowed = START_HOUR * 60;
    const maxAllowed = END_HOUR * 60 - duration;
    const newStartMins = Math.max(minAllowed, Math.min(maxAllowed, origStart + deltaMinutes));
    const newEndMins = newStartMins + duration;

    const newStartStr = toTimeString(newStartMins);
    const newEndStr = toTimeString(newEndMins);

    if (
      targetDayIndex !== block.day_of_week ||
      newStartStr !== block.start_time.slice(0, 5) ||
      newEndStr !== block.end_time.slice(0, 5)
    ) {
      await moveBlock(
        block.id,
        targetDayIndex,
        newStartStr,
        newEndStr,
        block.occurrence_date || undefined,
        'this'
      );
    }
  };

  const baseDate = parseISO(weekStart);
  const activeDays = viewMode === '5day' ? ALL_DAYS.slice(0, 5) : ALL_DAYS;
  const todayStr = getTodayDateStr(timezone);

  return (
    <ClientOnlyDnd>
      <DndContext
        sensors={sensors}
        onDragStart={(e) => setActiveDragBlock(e.active.data.current?.block || null)}
        onDragEnd={handleDragEnd}
      >
        <div className="w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-xl overflow-hidden flex flex-col text-[var(--text-primary)] transition-all">
          {/* Calendar Toolbar Legend */}
          <div className="px-4 py-2.5 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-4">
              <span className="font-bold text-[var(--text-muted)] text-[11px] uppercase tracking-wider">
                Event Categories:
              </span>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-xs shadow-blue-500/50" />
                <span className="font-semibold text-[var(--class-text)]">Class</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs shadow-emerald-500/50" />
                <span className="font-semibold text-[var(--shift-text)]">Work Shift</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-xs shadow-purple-500/50" />
                <span className="font-semibold text-[var(--study-text)]">Study (📖)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-xs shadow-rose-500/50 animate-pulse" />
                <span className="font-bold text-rose-600 dark:text-rose-400">
                  Conflict (⚠️)
                </span>
              </div>
            </div>

            <div className="text-[11px] text-[var(--text-muted)] hidden sm:block">
              Click empty slot to add · Drag to reschedule · Drag bottom to resize
            </div>
          </div>

          {/* Horizontal scroll container on mobile/tablet */}
          <div className="overflow-x-auto min-w-full">
            <div
              style={{
                minWidth: viewMode === '5day' ? '680px' : '900px',
              }}
              className="flex"
            >
              {/* Sticky Time Gutter Column */}
              <TimeGutter
                startHour={START_HOUR}
                endHour={END_HOUR}
                hourHeight={HOUR_HEIGHT}
              />

              {/* Day Columns */}
              <div className="flex-1 flex divide-x divide-[var(--border-color)]">
                {activeDays.map((d, i) => {
                  const dayDate = addDays(baseDate, i);
                  const dateIso = format(dayDate, 'yyyy-MM-dd');
                  const isToday = dateIso === todayStr;
                  const dayBlocks = blocks.filter(
                    (b) => b.day_of_week === d.index && !b.deleted
                  );

                  return (
                    <DayColumn
                      key={d.index}
                      dayIndex={d.index}
                      dayName={d.short}
                      dateStr={format(dayDate, 'MMM d')}
                      dayNumber={format(dayDate, 'd')}
                      isToday={isToday}
                      blocks={dayBlocks}
                      allBlocks={blocks}
                      conflicts={conflicts}
                      startHour={START_HOUR}
                      endHour={END_HOUR}
                      hourHeight={HOUR_HEIGHT}
                      onBlockClick={onBlockClick}
                      onBlockDelete={deleteBlock}
                      onBlockResize={resizeBlock}
                      onSlotClick={onSlotClick}
                      onReplanStudy={onReplanStudy}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Elevated Drag Overlay preview */}
        <DragOverlay>
          {activeDragBlock && (
            <div
              className={`rounded-lg border-2 px-3 py-2 shadow-2xl scale-[1.03] opacity-95 text-xs font-bold ring-2 ring-indigo-500/60 ${
                activeDragBlock.type === 'shift'
                  ? 'border-[var(--shift-border)] bg-[var(--shift-bg)] text-[var(--shift-text)]'
                  : activeDragBlock.type === 'study'
                  ? 'border-[var(--study-border)] bg-[var(--study-bg)] text-[var(--study-text)]'
                  : 'border-[var(--class-border)] bg-[var(--class-bg)] text-[var(--class-text)]'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span>
                  {activeDragBlock.type === 'shift'
                    ? '💼'
                    : activeDragBlock.type === 'study'
                    ? '📖'
                    : '📚'}
                </span>
                <span>{activeDragBlock.title}</span>
              </div>
              <div className="text-[10px] font-mono mt-0.5 opacity-80">
                {activeDragBlock.start_time.slice(0, 5)} – {activeDragBlock.end_time.slice(0, 5)}
              </div>
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </ClientOnlyDnd>
  );
}
