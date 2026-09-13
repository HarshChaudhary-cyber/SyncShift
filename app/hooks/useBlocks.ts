'use client';

import { useCalendar } from '@/context/CalendarContext';
import { BlockCreatePayload, BlockUpdatePayload } from '@/lib/api';

export function useBlocks() {
  const {
    blocks,
    loading,
    error,
    addBlock,
    updateBlock,
    deleteBlock,
    moveBlock,
    resizeBlock,
    refreshWeek,
  } = useCalendar();

  return {
    blocks,
    loading,
    error,
    addBlock: (payload: BlockCreatePayload) => addBlock(payload),
    updateBlock: (id: number, payload: BlockUpdatePayload) => updateBlock(id, payload),
    deleteBlock: (id: number, scope?: 'this' | 'future' | 'all', occurrenceDate?: string) =>
      deleteBlock(id, scope, occurrenceDate),
    moveBlock: (
      id: number,
      dayOfWeek: number,
      startTime: string,
      endTime: string,
      occurrenceDate?: string,
      scope?: 'this' | 'future' | 'all'
    ) => moveBlock(id, dayOfWeek, startTime, endTime, occurrenceDate, scope),
    resizeBlock: (
      id: number,
      endTime: string,
      occurrenceDate?: string,
      scope?: 'this' | 'future' | 'all'
    ) => resizeBlock(id, endTime, occurrenceDate, scope),
    refreshBlocks: refreshWeek,
  };
}
