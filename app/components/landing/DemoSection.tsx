'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  SparklesIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import CalendarWeekView, { TimeBlock } from '@/components/CalendarWeekView';
import ClientOnlyDnd from '@/components/ClientOnlyDnd';
import { detectConflicts } from '@/lib/schedule';

// Pre-loaded realistic fake data per spec:
// - CS101 Mon/Wed 9-10:30
// - MATH220 Tue/Thu 14-15:30 (with Wed recitation 14-15:30)
// - Café Shift Wed 14-18 (conflicts with MATH220!)
const INITIAL_DEMO_BLOCKS: TimeBlock[] = [
  {
    id: 'demo-cs101-mon',
    day: 'Monday',
    startTime: '09:00',
    endTime: '10:30',
    type: 'class',
    status: 'enrolled',
    label: 'CS101: Intro to CS',
    subLabel: 'Auditorium 2 · Prof. Vance',
  },
  {
    id: 'demo-cs101-wed',
    day: 'Wednesday',
    startTime: '09:00',
    endTime: '10:30',
    type: 'class',
    status: 'enrolled',
    label: 'CS101: Intro to CS',
    subLabel: 'Auditorium 2 · Prof. Vance',
  },
  {
    id: 'demo-math220-tue',
    day: 'Tuesday',
    startTime: '14:00',
    endTime: '15:30',
    type: 'class',
    status: 'enrolled',
    label: 'MATH220: Linear Algebra',
    subLabel: 'Hall B · Prof. Williams',
  },
  {
    id: 'demo-math220-wed',
    day: 'Wednesday',
    startTime: '14:00',
    endTime: '15:30',
    type: 'class',
    status: 'enrolled',
    label: 'MATH220: Linear Algebra',
    subLabel: 'Recitation Hall · TA David',
  },
  {
    id: 'demo-math220-thu',
    day: 'Thursday',
    startTime: '14:00',
    endTime: '15:30',
    type: 'class',
    status: 'enrolled',
    label: 'MATH220: Linear Algebra',
    subLabel: 'Hall B · Prof. Williams',
  },
  {
    id: 'demo-cafe-shift-wed',
    day: 'Wednesday',
    startTime: '14:00',
    endTime: '18:00',
    type: 'shift',
    status: 'enrolled',
    label: 'Café Barista Shift',
    subLabel: 'Campus Bistro · $16.50/hr',
    hourlyWage: 16.5,
  },
];

export default function DemoSection() {
  const [blocks, setBlocks] = useState<TimeBlock[]>(INITIAL_DEMO_BLOCKS);
  const [resolved, setResolved] = useState(false);

  // Compute live conflicts using SyncShift sweep-line detector
  const processedBlocks = useMemo(() => {
    return detectConflicts(blocks);
  }, [blocks]);

  const conflictCount = useMemo(() => {
    return processedBlocks.filter((b) => b.type === 'conflict').length;
  }, [processedBlocks]);

  const toggleConflict = () => {
    if (!resolved) {
      // Move Café shift to 16:00 - 20:00 on Wednesday or Friday to resolve conflict
      setBlocks((prev) =>
        prev.map((b) =>
          b.id === 'demo-cafe-shift-wed'
            ? { ...b, startTime: '16:00', endTime: '20:00', subLabel: 'Shift moved to avoid clash' }
            : b
        )
      );
      setResolved(true);
    } else {
      setBlocks(INITIAL_DEMO_BLOCKS);
      setResolved(false);
    }
  };

  return (
    <section
      id="demo"
      className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[#0a0a0a] border-t border-neutral-900/60 overflow-hidden"
    >
      {/* Ambient background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-900/10 rounded-full blur-[160px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] mb-4 shadow-sm"
          >
            <SparklesIcon className="w-4 h-4 text-indigo-400" />
            <span>Interactive Live Demo</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl md:text-5xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
          >
            See it{' '}
            <span className="bg-gradient-to-r from-red-400 via-rose-300 to-indigo-400 bg-clip-text text-transparent">
              in action
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-3 text-sm sm:text-base text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            Here is the actual SyncShift calendar engine running with sample university courses and a part-time job.
          </motion.p>
        </div>

        {/* Demo Card Frame */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.7 }}
          className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl p-4 sm:p-6 backdrop-blur-sm"
        >
          {/* Top Bar of the demo */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-[var(--border-color)]">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                Sample Week: Fall Semester
              </span>

              {/* Pulsing Conflict Badge */}
              <AnimatePresence mode="wait">
                {conflictCount > 0 ? (
                  <motion.div
                    key="conflict-badge"
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-950/80 border border-red-500/60 text-red-300 text-xs font-bold shadow-lg shadow-red-950/40"
                  >
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
                    </span>
                    <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />
                    <span>1 Conflict Detected (Wed 14:00)</span>
                  </motion.div>
                ) : (
                  <motion.div
                    key="resolved-badge"
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-xs font-bold"
                  >
                    <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
                    <span>0 Conflicts · Schedule Clean</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Interactive demo action button */}
            <button
              onClick={toggleConflict}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card)] text-[var(--text-primary)] text-xs font-medium transition cursor-pointer border border-[var(--border-color)]"
            >
              <ArrowPathIcon className="w-3.5 h-3.5" />
              <span>{resolved ? 'Reset to Initial Clash' : 'Simulate Resolving Shift'}</span>
            </button>
          </div>

          {/* Embedded Real Calendar Component in read-only mode */}
          <div className="w-full overflow-x-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]">
            <div className="min-w-[700px] h-[520px]">
              <ClientOnlyDnd
                fallback={
                  <div className="w-full h-full flex flex-col items-center justify-center text-[var(--text-muted)] gap-2">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs font-mono">Loading live calendar engine…</span>
                  </div>
                }
              >
                <CalendarWeekView
                  blocks={processedBlocks}
                  days={['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']}
                  startHour={8}
                  endHour={19}
                  snapMinutes={15}
                />
              </ClientOnlyDnd>
            </div>
          </div>

          {/* Bottom Footer Note & CTA */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-[var(--border-color)]">
            <div className="text-xs text-[var(--text-secondary)] text-center sm:text-left">
              <span className="font-semibold text-[var(--text-primary)]">Demo data only</span> — sign up to save your real university timetable & shifts.
            </div>

            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs tracking-tight transition-all duration-200 shadow-md hover:scale-[1.02] active:scale-[0.98]"
            >
              <span>Try with your own schedule</span>
              <ArrowRightIcon className="w-3.5 h-3.5" />
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
