'use client';

import React, { useEffect, useState } from 'react';
import { useAuthContext } from '@/context/AuthContext';

interface CurrentTimeIndicatorProps {
  startHour: number;
  endHour: number;
  hourHeight: number;
}

/**
 * Returns the current time minutes (from 00:00) and HH:MM string in the given IANA timezone.
 */
function getNowInTimezone(timeZone: string): { minutes: number; timeStr: string } {
  try {
    const formatter = new Intl.DateTimeFormat('en-GB', {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    const parts = formatter.formatToParts(new Date());
    const partMap: Record<string, string> = {};
    for (const p of parts) {
      partMap[p.type] = p.value;
    }
    const hour = parseInt(partMap.hour || '0', 10);
    const minute = parseInt(partMap.minute || '0', 10);
    return {
      minutes: hour * 60 + minute,
      timeStr: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    };
  } catch {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    return {
      minutes: hour * 60 + minute,
      timeStr: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    };
  }
}

export default function CurrentTimeIndicator({
  startHour,
  endHour,
  hourHeight,
}: CurrentTimeIndicatorProps) {
  const { user } = useAuthContext();
  const timezone =
    user?.timezone ||
    (typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'UTC');

  const [mounted, setMounted] = useState(false);
  const [nowData, setNowData] = useState(() => getNowInTimezone(timezone));

  useEffect(() => {
    setMounted(true);
    setNowData(getNowInTimezone(timezone));

    const interval = setInterval(() => {
      setNowData(getNowInTimezone(timezone));
    }, 60000);

    return () => clearInterval(interval);
  }, [timezone]);

  if (!mounted) return null;

  const minAllowed = startHour * 60;
  const maxAllowed = endHour * 60;

  if (nowData.minutes < minAllowed || nowData.minutes > maxAllowed) {
    return null;
  }

  const top = ((nowData.minutes - minAllowed) / 60) * hourHeight;

  return (
    <div
      style={{ top: `${top}px` }}
      aria-label={`Current time: ${nowData.timeStr}`}
      className="absolute left-0 right-0 z-30 pointer-events-none flex items-center -translate-y-1/2"
    >
      {/* Pulse circle on the left edge */}
      <div className="relative flex items-center justify-center -ml-1">
        <span className="absolute w-3 h-3 rounded-full bg-rose-500/40 animate-ping" />
        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm shadow-rose-500/80" />
      </div>

      {/* Red line spanning the column */}
      <div className="flex-1 h-[2px] bg-rose-500 shadow-xs shadow-rose-500/50" />

      {/* Time label badge on the right edge */}
      <span className="ml-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-rose-500 text-white shadow-xs select-none">
        {nowData.timeStr}
      </span>
    </div>
  );
}
