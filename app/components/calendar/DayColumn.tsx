'use client';

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { BlockOut, ConflictItem } from '@/lib/api';
import DayHeader from './DayHeader';
import CalendarBlockCard from './CalendarBlockCard';
import CurrentTimeIndicator from './CurrentTimeIndicator';

interface DayColumnProps {
  dayIndex: number;
  dayName: string;
  dateStr: string;
  dayNumber: string;
  isToday: boolean;
  blocks: BlockOut[];
  allBlocks?: BlockOut[];
  conflicts: ConflictItem[];
  startHour: number;
  endHour: number;
  hourHeight: number;
  onBlockClick: (block: BlockOut) => void;
  onBlockDelete: (id: number, scope?: 'this' | 'future' | 'all', occurrenceDate?: string) => void;
  onBlockResize: (id: number, newEndTime: string, occurrenceDate?: string) => void;
  onSlotClick?: (dayIndex: number, startTime: string, endTime: string) => void;
  onReplanStudy?: (taskId: number) => Promise<void> | void;
}

export default function DayColumn({
  dayIndex,
  dayName,
  dateStr,
  dayNumber,
  isToday,
  blocks,
  allBlocks,
  conflicts,
  startHour,
  endHour,
  hourHeight,
  onBlockClick,
  onBlockDelete,
  onBlockResize,
  onSlotClick,
  onReplanStudy,
}: DayColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `day-${dayIndex}`,
    data: { dayIndex },
  });

  const totalHours = endHour - startHour;

  const handleGridClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Prevent triggering slot click if click originated from a block card
    if ((e.target as HTMLElement).closest('[data-block-card]')) return;
    if (!onSlotClick) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const relY = e.clientY - rect.top;
    const clickedMins = Math.round((relY / hourHeight) * 60 / 15) * 15;
    const startMins = Math.max(0, Math.min(clickedMins, (endHour - startHour) * 60 - 60));
    const endMins = startMins + 60;
    const fmt = (m: number) =>
      `${String(startHour + Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
    onSlotClick(dayIndex, fmt(startMins), fmt(endMins));
  };

  return (
    <div
      className={`flex-1 min-w-[125px] sm:min-w-[140px] border-r border-[var(--border-color)] last:border-r-0 flex flex-col transition-colors ${
        isToday ? 'bg-indigo-500/[0.02] dark:bg-indigo-950/[0.05]' : 'bg-transparent'
      }`}
    >
      {/* Column Header */}
      <DayHeader
        dayName={dayName}
        dateStr={dateStr}
        dayNumber={dayNumber}
        isToday={isToday}
        dayBlocks={blocks}
      />

      {/* Grid container with droppable area */}
      <div
        ref={setNodeRef}
        onClick={handleGridClick}
        style={{ height: `${totalHours * hourHeight}px` }}
        className={`relative transition-colors cursor-cell ${
          isOver
            ? 'bg-indigo-500/15 ring-2 ring-inset ring-indigo-500/50'
            : 'hover:bg-black/[0.01] dark:hover:bg-white/[0.01]'
        }`}
      >
        {/* Hour line background */}
        {Array.from({ length: totalHours }).map((_, idx) => (
          <React.Fragment key={idx}>
            {/* Main hour solid line */}
            <div
              style={{ top: `${idx * hourHeight}px` }}
              className="absolute left-0 right-0 border-b border-[var(--border-color)]/70 pointer-events-none"
            />
            {/* Half-hour subtle dashed line */}
            <div
              style={{ top: `${idx * hourHeight + hourHeight / 2}px` }}
              className="absolute left-0 right-0 border-b border-dashed border-[var(--border-color)]/35 pointer-events-none"
            />
          </React.Fragment>
        ))}

        {/* Current Time Indicator (rendered only on today's column) */}
        {isToday && (
          <CurrentTimeIndicator
            startHour={startHour}
            endHour={endHour}
            hourHeight={hourHeight}
          />
        )}

        {/* Blocks rendered in this day */}
        {blocks.map((block) => (
          <CalendarBlockCard
            key={block.occurrence_date ? `${block.id}-${block.occurrence_date}` : block.id}
            block={block}
            allBlocks={allBlocks}
            conflicts={conflicts}
            hourHeight={hourHeight}
            startHour={startHour}
            onClick={onBlockClick}
            onDelete={onBlockDelete}
            onResizeEnd={onBlockResize}
            onReplanStudy={onReplanStudy}
          />
        ))}
      </div>
    </div>
  );
}
