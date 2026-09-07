'use client';

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { BlockOut, ConflictItem } from '@/lib/api';
import CalendarBlockCard from './CalendarBlockCard';

interface DayColumnProps {
  dayIndex: number;
  dayName: string;
  dateStr: string;
  blocks: BlockOut[];
  conflicts: ConflictItem[];
  startHour: number;
  endHour: number;
  hourHeight: number;
  onBlockClick: (block: BlockOut) => void;
  onBlockDelete: (id: number) => void;
  onBlockResize: (id: number, newEndTime: string) => void;
  onSlotClick?: (dayIndex: number, startTime: string, endTime: string) => void;
}

export default function DayColumn({
  dayIndex,
  dayName,
  dateStr,
  blocks,
  conflicts,
  startHour,
  endHour,
  hourHeight,
  onBlockClick,
  onBlockDelete,
  onBlockResize,
  onSlotClick,
}: DayColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `day-${dayIndex}`,
    data: { dayIndex },
  });

  const totalHours = endHour - startHour;

  const handleGridClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only fire if the click is directly on the grid (not on a block card)
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
    <div className="flex-1 min-w-[130px] border-r border-neutral-800 last:border-r-0 flex flex-col">
      {/* Column Header */}
      <div className="py-2.5 px-2 text-center border-b border-neutral-800 bg-neutral-900/60 sticky top-0 z-20 backdrop-blur-xs">
        <p className="text-xs font-semibold text-neutral-200">{dayName}</p>
        <p className="text-[10px] text-neutral-400">{dateStr}</p>
      </div>

      {/* Grid container with droppable area */}
      <div
        ref={setNodeRef}
        onClick={handleGridClick}
        style={{ height: `${totalHours * hourHeight}px` }}
        className={`relative transition-colors cursor-cell ${
          isOver ? 'bg-blue-500/10 ring-2 ring-inset ring-blue-500/40' : 'bg-transparent'
        }`}
      >
        {/* Hour line background */}
        {Array.from({ length: totalHours }).map((_, idx) => (
          <div
            key={idx}
            style={{ height: `${hourHeight}px`, top: `${idx * hourHeight}px` }}
            className="absolute left-0 right-0 border-b border-neutral-800/50 pointer-events-none"
          />
        ))}

        {/* Blocks rendered in this day */}
        {blocks.map((block) => (
          <CalendarBlockCard
            key={block.id}
            block={block}
            conflicts={conflicts}
            hourHeight={hourHeight}
            startHour={startHour}
            onClick={onBlockClick}
            onDelete={onBlockDelete}
            onResizeEnd={onBlockResize}
          />
        ))}
      </div>
    </div>
  );
}
