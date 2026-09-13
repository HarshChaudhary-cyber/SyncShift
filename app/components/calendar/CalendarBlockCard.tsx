'use client';

import React, { useState, useRef } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { BlockOut, ConflictItem } from '@/lib/api';
import EventHoverCard from './EventHoverCard';

interface CalendarBlockCardProps {
  block: BlockOut;
  allBlocks?: BlockOut[];
  conflicts: ConflictItem[];
  hourHeight: number;
  startHour: number;
  onClick: (block: BlockOut) => void;
  onDelete?: (id: number, scope?: 'this' | 'future' | 'all', occurrenceDate?: string) => void;
  onResizeEnd: (id: number, newEndTime: string, occurrenceDate?: string) => void;
  onReplanStudy?: (taskId: number) => Promise<void> | void;
}

export default function CalendarBlockCard({
  block,
  allBlocks,
  conflicts,
  hourHeight,
  startHour,
  onClick,
  onDelete,
  onResizeEnd,
  onReplanStudy,
}: CalendarBlockCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const draggableId = block.occurrence_date
    ? `block-${block.id}-${block.occurrence_date}`
    : `block-${block.id}`;

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: draggableId,
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
  const duration = Math.max(15, endMins - startMins);
  const top = ((startMins - startHour * 60) / 60) * hourHeight;
  const height = (duration / 60) * hourHeight;

  // Identify active conflict involving this block
  const activeConflict = conflicts.find(
    (c) => c.block_a_id === block.id || c.block_b_id === block.id
  );

  const conflictingBlockId = activeConflict
    ? activeConflict.block_a_id === block.id
      ? activeConflict.block_b_id
      : activeConflict.block_a_id
    : null;

  const conflictingBlock = allBlocks?.find((b) => b.id === conflictingBlockId);

  const studyTaskId =
    (block.type === 'study' ? block.study_task_id : null) ||
    (conflictingBlock?.type === 'study' ? conflictingBlock?.study_task_id : null);

  const style: React.CSSProperties = {
    top: `${Math.max(0, top)}px`,
    height: `${Math.max(28, height)}px`,
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    zIndex: isDragging ? 50 : isHovered ? 40 : 10,
    opacity: isDragging ? 0.8 : block.isSaving ? 0.65 : 1,
  };

  const handleMouseEnter = () => {
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovered(true);
    }, 150);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    setIsHovered(false);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    if (confirm(`Delete "${block.title}"?`)) {
      onDelete?.(block.id, block.is_recurring ? 'this' : 'all', block.occurrence_date || undefined);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(block);
    }
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const startY = e.clientY;
    const initialHeight = height;

    const onMouseMove = (moveEvent: MouseEvent) => {
      // Visual feedback handled on mouseup
    };

    const onMouseUp = (upEvent: MouseEvent) => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      const deltaY = upEvent.clientY - startY;
      const newHeight = Math.max(24, initialHeight + deltaY);
      const newDuration = Math.round((newHeight / hourHeight) * 60 / 15) * 15;
      const targetEndMins = startMins + Math.max(15, newDuration);
      onResizeEnd(block.id, formatMinutes(targetEndMins), block.occurrence_date || undefined);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  // Base semantic category styles (preserved even when in conflict)
  const baseCategoryStyle =
    block.type === 'shift'
      ? 'border-[var(--shift-border)] bg-[var(--shift-bg)] text-[var(--shift-text)]'
      : block.type === 'study'
        ? 'border-[var(--study-border)] bg-[var(--study-bg)] text-[var(--study-text)]'
        : 'border-[var(--class-border)] bg-[var(--class-bg)] text-[var(--class-text)]';

  // Conflict modifier: retains category identity while strongly alerting
  const conflictModifier = activeConflict
    ? '!border-rose-500 ring-2 ring-rose-500/70 shadow-md shadow-rose-500/20'
    : 'shadow-xs hover:shadow-md';

  const isShortBlock = duration <= 35;
  const isMediumBlock = duration > 35 && duration <= 55;

  const ariaLabel = `${block.title}, ${block.type} event, ${block.start_time.slice(0, 5)} to ${block.end_time.slice(0, 5)}${block.location ? `, at ${block.location}` : ''
    }${activeConflict ? `, conflicting: ${activeConflict.overlap_minutes} minutes overlap` : ''}`;

  return (
    <div
      ref={setNodeRef}
      aria-label={ariaLabel}
      style={style}
      data-block-card="true"
      {...attributes}
      {...listeners}
      onClick={() => onClick(block)}
      onKeyDown={handleKeyDown}
      onContextMenu={handleContextMenu}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`group absolute left-1 right-1 rounded-lg border px-2 py-1 select-none transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${block.isSaving
          ? 'pointer-events-none ring-1 ring-blue-400/50'
          : isDragging
            ? 'cursor-grabbing shadow-2xl scale-[1.02]'
            : 'cursor-grab active:cursor-grabbing hover:-translate-y-0.5'
        } ${baseCategoryStyle} ${conflictModifier}`}
    >
      {/* Top row: Title + Saving/Conflict badges */}
      <div className="flex items-start justify-between gap-1 overflow-hidden leading-tight">
        <div className="flex items-center gap-1 min-w-0 font-semibold text-xs truncate">
          {block.type === 'shift' && <span className="shrink-0 text-[11px]" title="Work Shift">💼</span>}
          {block.type === 'study' && <span className="shrink-0 text-[11px]" title="Study Session">📖</span>}
          {block.type === 'class' && <span className="shrink-0 text-[11px]" title="Class Timetable">📚</span>}
          <span className="truncate">{block.title}</span>
          {block.is_recurring && (
            <span className="shrink-0 text-[10px] opacity-70" title={block.recurrence_interval === 2 ? 'Repeats every 2 weeks' : 'Repeats weekly'}>
              🔁
            </span>
          )}
          {block.is_exception && (
            <span className="shrink-0 text-[9px] px-1 rounded bg-amber-500/20 text-amber-500 border border-amber-500/30" title="Modified occurrence">
              mod
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {block.isSaving && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 bg-blue-600 text-white rounded animate-pulse">
              SAVING
            </span>
          )}
          {activeConflict && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 bg-rose-600 text-white rounded flex items-center gap-0.5 shadow-xs">
              <span>⚠️</span>
              {!isShortBlock && <span>CONFLICT</span>}
            </span>
          )}
        </div>
      </div>

      {/* Second row: Time & Location (adapted for short blocks) */}
      {!isShortBlock && (
        <div className="flex items-center gap-1.5 text-[11px] opacity-90 mt-0.5 font-mono">
          <span>
            {block.start_time.slice(0, 5)}–{block.end_time.slice(0, 5)}
          </span>
          {block.location && !isMediumBlock && (
            <span className="truncate font-sans opacity-75">· {block.location}</span>
          )}
        </div>
      )}

      {/* Third row: Conflict overlap summary & Auto-replan if Study */}
      {activeConflict && !isShortBlock && (
        <div className="mt-1 flex items-center justify-between gap-1 text-[10px] font-medium text-rose-600 dark:text-rose-400">
          <span className="truncate">
            ⚠️ {activeConflict.overlap_minutes}m overlap
          </span>
          {studyTaskId && onReplanStudy && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onReplanStudy(studyTaskId);
              }}
              className="px-1.5 py-0.2 bg-purple-600 hover:bg-purple-500 text-white rounded text-[9px] font-semibold transition cursor-pointer"
              title="Automatically move study session into an open free gap"
            >
              🔄 Replan
            </button>
          )}
        </div>
      )}

      {/* Resize Bottom Handle */}
      <div
        onMouseDown={handleResizeStart}
        title="Drag edge to resize duration"
        aria-label="Resize duration"
        className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize hover:bg-black/15 dark:hover:bg-white/20 rounded-b-lg transition"
      />

      {/* Floating Hover Card (visible on hover when not dragging) */}
      {isHovered && !isDragging && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-[calc(100%+8px)] hidden md:block">
          <EventHoverCard
            block={block}
            activeConflict={activeConflict}
            conflictingBlock={conflictingBlock}
            durationMinutes={duration}
          />
        </div>
      )}
    </div>
  );
}
