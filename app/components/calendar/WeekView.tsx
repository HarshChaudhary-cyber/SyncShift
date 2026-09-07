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
import { BlockOut } from '@/lib/api';
import DayColumn from './DayColumn';

interface WeekViewProps {
  onBlockClick: (block: BlockOut) => void;
  onSlotClick?: (dayIndex: number, startTime: string, endTime: string) => void;
}

const START_HOUR = 6;
const END_HOUR = 22;
const HOUR_HEIGHT = 60;
const DAYS = [
  { index: 1, name: 'Monday' },
  { index: 2, name: 'Tuesday' },
  { index: 3, name: 'Wednesday' },
  { index: 4, name: 'Thursday' },
  { index: 5, name: 'Friday' },
];

export default function WeekView({ onBlockClick, onSlotClick }: WeekViewProps) {
  const { blocks, conflicts, weekStart, moveBlock, resizeBlock, deleteBlock } = useCalendar();
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
    const targetDayIndex = over?.data?.current?.dayIndex ?? block.day_of_week;

    const origStart = parseMinutes(block.start_time);
    const origEnd = parseMinutes(block.end_time);
    const duration = origEnd - origStart;

    const deltaMinutes = Math.round((delta.y / HOUR_HEIGHT) * 60 / 15) * 15;
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
      await moveBlock(block.id, targetDayIndex, newStartStr, newEndStr);
    }
  };

  const baseDate = parseISO(weekStart);
  const totalHours = END_HOUR - START_HOUR;

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(e) => setActiveDragBlock(e.active.data.current?.block || null)}
      onDragEnd={handleDragEnd}
    >
      <div className="w-full bg-neutral-900/80 border border-neutral-800 rounded-xl shadow-xl overflow-hidden backdrop-blur-xs flex flex-col">
        {/* Horizontal scroll on mobile */}
        <div className="overflow-x-auto min-w-full">
          <div className="min-w-[720px] flex">
            {/* Time Gutter Column */}
            <div className="w-16 shrink-0 border-r border-neutral-800 bg-neutral-950/40">
              <div className="h-[49px] border-b border-neutral-800" />
              <div style={{ height: `${totalHours * HOUR_HEIGHT}px` }} className="relative">
                {Array.from({ length: totalHours }).map((_, idx) => {
                  const hour = START_HOUR + idx;
                  const displayHour = hour === 12 ? '12 PM' : hour > 12 ? `${hour - 12} PM` : `${hour} AM`;
                  return (
                    <div
                      key={hour}
                      style={{ top: `${idx * HOUR_HEIGHT}px` }}
                      className="absolute left-0 right-0 pr-2 -translate-y-2 text-right text-[11px] font-mono text-neutral-500"
                    >
                      {displayHour}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 5 Day Columns (Mon - Fri) */}
            <div className="flex-1 flex divide-x divide-neutral-800">
              {DAYS.map((d, i) => {
                const dayDate = addDays(baseDate, i);
                const dayBlocks = blocks.filter((b) => b.day_of_week === d.index && !b.deleted);

                return (
                  <DayColumn
                    key={d.index}
                    dayIndex={d.index}
                    dayName={d.name}
                    dateStr={format(dayDate, 'MMM d')}
                    blocks={dayBlocks}
                    conflicts={conflicts}
                    startHour={START_HOUR}
                    endHour={END_HOUR}
                    hourHeight={HOUR_HEIGHT}
                    onBlockClick={onBlockClick}
                    onBlockDelete={deleteBlock}
                    onBlockResize={resizeBlock}
                    onSlotClick={onSlotClick}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <DragOverlay>
        {activeDragBlock && (
          <div className="rounded-lg border border-blue-400 bg-blue-900/90 text-white p-2.5 shadow-2xl opacity-90 text-xs font-semibold">
            {activeDragBlock.title}
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
