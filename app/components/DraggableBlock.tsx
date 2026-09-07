'use client';

import React, { useCallback, useRef, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import type { TimeBlock } from './CalendarWeekView';


export interface DraggableBlockProps {
  block: TimeBlock;
  topPct: string;
  heightPct: string;
  styles: { container: string; badge: string; tag: string; zIndex: string };
  activeId: string | number | null;
  onBlockClick?: (block: TimeBlock) => void;
  onResizeEnd: (blockId: string | number, deltaMinutes: number) => void;
  minutesPerPixel: number;
  snapMinutes: number;
  /** 12-hour format string, e.g. "1:30 PM" */
  startLabel: string;
  endLabel: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Snaps a value to the nearest multiple of `step` */
function snapTo(value: number, step: number): number {
  return Math.round(value / step) * step;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DraggableBlock: React.FC<DraggableBlockProps> = ({
  block,
  topPct,
  heightPct,
  styles,
  activeId,
  onBlockClick,
  onResizeEnd,
  minutesPerPixel,
  snapMinutes,
  startLabel,
  endLabel,
}) => {
  const blockId = block.id ?? `${block.day}-fallback`;
  const isConflict = block.type === 'conflict';

  // ── Drag (dnd-kit) ──────────────────────────────────────────────────────
  const {
    attributes,
    listeners,
    setNodeRef: setDragRef,
    transform,
    isDragging,
  } = useDraggable({
    id: `block-${blockId}`,
    data: { block },
    disabled: isConflict || Boolean(block.isSaving),
  });

  // ── Resize (native pointer events) ──────────────────────────────────────
  const [resizeDeltaPx, setResizeDeltaPx] = useState(0);
  const isResizing = useRef(false);
  const startY = useRef(0);
  // Track whether this was a click or a drag to distinguish onBlockClick
  const didDragOrResize = useRef(false);

  const handleResizePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (isConflict) return;
      e.stopPropagation(); // don't trigger block drag
      e.preventDefault();
      isResizing.current = true;
      didDragOrResize.current = true;
      startY.current = e.clientY;
      setResizeDeltaPx(0);
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [isConflict],
  );

  const handleResizePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isResizing.current) return;
      const rawDelta = e.clientY - startY.current;
      // Snap the pixel delta to the nearest grid line
      const snapPx = snapMinutes / minutesPerPixel; // px per snap increment
      const snappedDelta = Math.round(rawDelta / snapPx) * snapPx;
      setResizeDeltaPx(snappedDelta);
    },
    [minutesPerPixel, snapMinutes],
  );

  const handleResizePointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!isResizing.current) return;
      isResizing.current = false;
      const rawDelta = e.clientY - startY.current;
      const deltaMinutes = snapTo(rawDelta * minutesPerPixel, snapMinutes);
      setResizeDeltaPx(0);
      if (deltaMinutes !== 0 && block.id != null) {
        onResizeEnd(block.id, deltaMinutes);
      }
      // Reset after a tick so the click handler can check it
      requestAnimationFrame(() => {
        didDragOrResize.current = false;
      });
    },
    [block.id, minutesPerPixel, onResizeEnd, snapMinutes],
  );

  const handleClick = useCallback(() => {
    if (didDragOrResize.current) return;
    onBlockClick?.(block);
  }, [block, onBlockClick]);

  // ── Style computation ───────────────────────────────────────────────────
  const isBeingDragged = isDragging || activeId === `block-${blockId}`;

  // During drag, the visual position stays and we render a DragOverlay
  // separately — but we still show a ghost in-place with reduced opacity.
  const dragStyle: React.CSSProperties = {
    top: topPct,
    height: resizeDeltaPx
      ? `calc(${heightPct} + ${resizeDeltaPx}px)`
      : heightPct,
    // When being dragged via dnd-kit transform, apply translate
    transform: transform
      ? `translateY(${transform.y}px)`
      : undefined,
    opacity: isBeingDragged ? 0.5 : block.isSaving ? 0.65 : 1,
    transition: isBeingDragged ? 'none' : 'opacity 150ms ease',
  };

    const isTentative = block.status === 'tentative';

    return (
      <div
        ref={setDragRef}
        role="button"
        tabIndex={0}
        aria-label={`${block.label} from ${startLabel} to ${endLabel}`}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onBlockClick?.(block);
        }}
        style={dragStyle}
        className={`absolute left-1 right-1 rounded-md p-1.5 overflow-hidden cursor-pointer flex flex-col justify-between transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-indigo-500 ${styles.container} ${styles.zIndex} ${
          isTentative ? 'border-dashed opacity-85 ring-1 ring-amber-400/50' : ''
        } ${
          block.isSaving ? 'pointer-events-none ring-1 ring-indigo-400/50' : isConflict ? '' : 'cursor-grab active:cursor-grabbing'
        }`}
        title={`${block.label} — ${startLabel} to ${endLabel}${block.status === 'tentative' ? ' (What-If Sandbox)' : ''}${block.isSaving ? ' (Saving changes...)' : ''}`}
        {...(isConflict || block.isSaving ? {} : { ...attributes, ...listeners })}
      >
        {/* Block content */}
        <div className="flex flex-col min-h-0">
          <div className="flex items-start justify-between gap-1">
            <span className="font-semibold text-xs leading-tight line-clamp-1">
              {block.label}
            </span>
            <div className="flex items-center gap-1 shrink-0">
              {block.isSaving && (
                <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded leading-none bg-indigo-200 text-indigo-900 dark:bg-indigo-900/90 dark:text-indigo-200 font-bold animate-pulse border border-indigo-400/60">
                  Saving…
                </span>
              )}
              {isTentative && (
                <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded leading-none bg-amber-200 text-amber-900 dark:bg-amber-900/80 dark:text-amber-200 font-bold border border-amber-400">
                  What-If
                </span>
              )}
              {isConflict && block.conflictMetadata?.actionableParty && (
                <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded leading-none bg-rose-200 text-rose-900 dark:bg-rose-900 dark:text-rose-200 font-bold">
                  {block.conflictMetadata.actionableParty === 'shift' ? 'Swap Shift' : 'Review'}
                </span>
              )}
              {block.isOvernight && (
                <span className="text-[8px] px-1 py-0.5 rounded leading-none bg-purple-200 text-purple-900 dark:bg-purple-900/80 dark:text-purple-200 font-medium">
                  {block.isOvernightFragment === 'spillover' ? '🌙 +1d' : '🌙 Night'}
                </span>
              )}
              <span
                className={`text-[9px] px-1 py-0.5 rounded leading-none shrink-0 ${styles.badge}`}
              >
                {styles.tag}
              </span>
            </div>
          </div>
          {(block.subLabel || block.hourlyWage != null || block.conflictMetadata?.actionableSuggestion) && (
            <span className="text-[10px] opacity-75 line-clamp-1 mt-0.5">
              {block.conflictMetadata?.actionableSuggestion || block.subLabel}
              {block.hourlyWage != null && ` · $${block.hourlyWage}/hr`}
            </span>
          )}
        </div>
        <div className="text-[10px] font-mono opacity-90 mt-1 shrink-0 flex items-center justify-between">
          <span>{startLabel} – {endLabel}</span>
          {block.isOvernight && (
            <span className="text-[9px] text-purple-700 dark:text-purple-300 font-sans font-medium">
              {block.isOvernightFragment === 'spillover' ? 'Part 2' : '+1 day'}
            </span>
          )}
        </div>

      {/* ── Resize handle (bottom edge) ────────────────────────────────── */}
      {!isConflict && (
        <div
          onPointerDown={handleResizePointerDown}
          onPointerMove={handleResizePointerMove}
          onPointerUp={handleResizePointerUp}
          className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize z-30 group"
          style={{ touchAction: 'none' }}
        >
          {/* Visual indicator — appears on hover */}
          <div className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full bg-current opacity-0 group-hover:opacity-30 transition-opacity" />
        </div>
      )}
    </div>
  );
};

export default DraggableBlock;
