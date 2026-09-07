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
    deleteBlock: (id: number) => deleteBlock(id),
    moveBlock: (id: number, dayOfWeek: number, startTime: string, endTime: string) =>
      moveBlock(id, dayOfWeek, startTime, endTime),
    resizeBlock: (id: number, endTime: string) => resizeBlock(id, endTime),
    refreshBlocks: refreshWeek,
  };
}
