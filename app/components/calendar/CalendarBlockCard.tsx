'use client';

import React from 'react';
import { useDraggable } from '@dnd-kit/core';
import { BlockOut, ConflictItem } from '@/lib/api';

interface CalendarBlockCardProps {
  block: BlockOut;
  conflicts: ConflictItem[];
  hourHeight: number;
  startHour: number;
  onClick: (block: BlockOut) => void;
  onDelete: (id: number) => void;
  onResizeEnd: (id: number, newEndTime: string) => void;
}

export default function CalendarBlockCard({
  block,
  conflicts,
  hourHeight,
  startHour,
  onClick,
  onDelete,
  onResizeEnd,
}: CalendarBlockCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `block-${block.id}`,
    data: { block },
    disabled: Boolean(block.isSaving),
  });

  const parseToMinutes = (timeStr: string) => {
    const parts = timeStr.split(':');
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  };

  const formatMinutes = (minutes: number) => {
    const clamped = Math.max(0, Math.min(24 * 60 - 1, minutes));
    const h = Math.floor(clamped / 60);
    const m = clamped % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  };

  const startMins = parseToMinutes(block.start_time);
  const endMins = parseToMinutes(block.end_time);
  const duration = Math.max(30, endMins - startMins);
  const top = ((startMins - startHour * 60) / 60) * hourHeight;
  const height = (duration / 60) * hourHeight;

  const activeConflict = conflicts.find(
    (c) => c.block_a_id === block.id || c.block_b_id === block.id
  );

  const style: React.CSSProperties = {
    top: `${Math.max(0, top)}px`,
    height: `${Math.max(32, height)}px`,
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    zIndex: isDragging ? 40 : 10,
    opacity: isDragging ? 0.75 : block.isSaving ? 0.6 : 1,
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    if (confirm(`Delete "${block.title}"?`)) {
      onDelete(block.id);
    }
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const startY = e.clientY;
    const initialHeight = height;

    const onMouseUp = (upEvent: MouseEvent) => {
      window.removeEventListener('mouseup', onMouseUp);
      const deltaY = upEvent.clientY - startY;
      const newHeight = Math.max(30, initialHeight + deltaY);
      const newDuration = Math.round((newHeight / hourHeight) * 60 / 15) * 15;
      const targetEndMins = startMins + Math.max(15, newDuration);
      onResizeEnd(block.id, formatMinutes(targetEndMins));
    };

    window.addEventListener('mouseup', onMouseUp);
  };

  // Type & conflict styles using CSS variables or Tailwind
  const colorClass = activeConflict
    ? 'border-rose-500 bg-rose-950/70 text-rose-200'
    : block.type === 'shift'
    ? 'border-emerald-500/70 bg-emerald-950/50 text-emerald-200'
    : 'border-blue-500/70 bg-blue-950/50 text-blue-200';

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-block-card="true"
      {...attributes}
      {...listeners}
      onClick={() => onClick(block)}
      onContextMenu={handleContextMenu}
      className={`absolute left-1 right-1 rounded-lg border px-2.5 py-1.5 shadow-sm select-none transition-shadow ${
        block.isSaving
          ? 'pointer-events-none ring-1 ring-blue-400/50'
          : 'cursor-grab active:cursor-grabbing'
      } ${colorClass}`}
    >
      <div className="flex items-start justify-between gap-1 overflow-hidden">
        <span className="font-semibold text-xs leading-tight truncate text-neutral-100">
          {block.title}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {block.isSaving && (
            <span className="shrink-0 text-[9px] font-bold px-1.5 py-0.5 bg-blue-600/80 text-white rounded animate-pulse">
              SAVING…
            </span>
          )}
          {activeConflict && (
            <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.2 bg-rose-500 text-white rounded">
              CONFLICT
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-[11px] text-neutral-300 mt-0.5">
        <span>{block.start_time.slice(0, 5)} - {block.end_time.slice(0, 5)}</span>
        {block.location && <span className="truncate opacity-75">· {block.location}</span>}
      </div>

      {activeConflict && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-rose-300 font-medium">
          <span>⚠️ {activeConflict.overlap_minutes}m overlap</span>
          <span className="uppercase text-[9px] px-1 bg-rose-900/60 rounded">
            {activeConflict.severity}
          </span>
        </div>
      )}

      {/* Resize Bottom Handle */}
      <div
        onMouseDown={handleResizeStart}
        className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize hover:bg-white/20 rounded-b-lg"
      />
    </div>
  );
}
