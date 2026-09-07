'use client';

import { useCalendar } from '@/context/CalendarContext';
import { ConflictItem } from '@/lib/api';

export function useConflicts() {
  const { conflicts, totals, refreshConflicts, loading } = useCalendar();

  const getConflictsForBlock = (blockId: number): ConflictItem[] => {
    return conflicts.filter(
      (c) => c.block_a_id === blockId || c.block_b_id === blockId
    );
  };

  const hasConflict = (blockId: number): boolean => {
    return conflicts.some(
      (c) => c.block_a_id === blockId || c.block_b_id === blockId
    );
  };

  return {
    conflicts,
    totals,
    loading,
    refreshConflicts,
    getConflictsForBlock,
    hasConflict,
  };
}
