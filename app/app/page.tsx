'use client';

import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import LandingHero from '@/components/LandingHero';
import CalendarWeekView, { TimeBlock } from '@/components/CalendarWeekView';
import { BlockFormModal } from '@/components/BlockFormModal';
import { ImportSummaryModal } from '@/components/ImportSummaryModal';
import { detectConflicts, calculateWeeklyWorkHours } from '@/lib/schedule';
import {
  parseIcsTimetable,
  sectionToTimeBlock,
  type Section,
  type ReviewItem,
} from '@/lib/icsParser';
import { getMondayOfWeek, dayToNumber } from '@/lib/calendarHelpers';
import { showErrorToast, showSuccessToast } from '@/lib/toast';
import { API_BASE, getAuthToken } from '@/lib/api';

// ---------------------------------------------------------------------------
// Seed data — class + shift blocks only (conflicts are computed live)
// Seed classes have isImported: true so they are replaced when a real timetable is imported
// ---------------------------------------------------------------------------

const SEED_BLOCKS: TimeBlock[] = [
  {
    id: 1,
    day: 'Monday',
    startTime: '09:00',
    endTime: '10:30',
    type: 'class',
    status: 'enrolled',
    label: 'CS 210: Data Structures',
    subLabel: 'Room 302, Prof. Sharma',
    isImported: true,
  },
  {
    id: 2,
    day: 'Monday',
    startTime: '10:00',
    endTime: '14:00',
    type: 'shift',
    status: 'enrolled',
    label: 'Campus Library Desk',
    subLabel: 'Shift Supervisor: Sarah',
    hourlyWage: 17.5,
  },
  {
    id: 4,
    day: 'Tuesday',
    startTime: '09:30',
    endTime: '11:00',
    type: 'class',
    status: 'enrolled',
    label: 'CS 210: Data Structures',
    subLabel: 'Room 302',
    isImported: true,
  },
  {
    id: 5,
    day: 'Tuesday',
    startTime: '13:00',
    endTime: '17:00',
    type: 'shift',
    status: 'enrolled',
    label: 'IT Helpdesk Shift',
    subLabel: 'Student Services Bldg',
    hourlyWage: 18.5,
  },
  {
    id: 6,
    day: 'Wednesday',
    startTime: '14:00',
    endTime: '17:00',
    type: 'class',
    status: 'enrolled',
    label: 'PHYS 150 Lab',
    subLabel: 'Lab B, TA: Chen',
    isImported: true,
  },
  {
    id: 7,
    day: 'Wednesday',
    startTime: '16:00',
    endTime: '20:00',
    type: 'shift',
    status: 'enrolled',
    label: 'Dining Hall Cashier',
    subLabel: 'Main Cafeteria',
    hourlyWage: 16.0,
  },
  {
    id: 9,
    day: 'Thursday',
    startTime: '11:00',
    endTime: '12:30',
    type: 'class',
    status: 'enrolled',
    label: 'MATH 220: Linear Algebra',
    subLabel: 'Hall C, Prof. Williams',
    isImported: true,
  },
  {
    id: 10,
    day: 'Thursday',
    startTime: '14:00',
    endTime: '18:00',
    type: 'shift',
    status: 'enrolled',
    label: 'Library Circulation Desk',
    subLabel: '2nd Floor',
    hourlyWage: 17.5,
  },
  {
    id: 11,
    day: 'Friday',
    startTime: '10:00',
    endTime: '11:30',
    type: 'class',
    status: 'enrolled',
    label: 'ENG 201: Technical Writing',
    subLabel: 'Room 105',
    isImported: true,
  },
  {
    id: 12,
    day: 'Sunday',
    startTime: '22:00',
    endTime: '02:00',
    type: 'shift',
    status: 'enrolled',
    isOvernight: true,
    durationMinutes: 240,
    label: 'Campus Security Night Shift',
    subLabel: 'Main Gate · Overnight (2h this week, 2h next week)',
    hourlyWage: 20.0,
  },
];

// ---------------------------------------------------------------------------
// How-It-Works section data
// ---------------------------------------------------------------------------

const HOW_IT_WORKS_STEPS = [
  {
    number: '01',
    title: 'Import your schedule',
    description:
      'Upload your university .ics file and enter your weekly work shifts via CSV or manual entry.',
  },
  {
    number: '02',
    title: 'Detect conflicts',
    description:
      'Our algorithm sweeps every time block, flags overlapping classes and shifts, and highlights them instantly.',
  },
  {
    number: '03',
    title: 'Visualise & resolve',
    description:
      'See conflicts colour-coded on a clean week view. Know exactly where the problems are before your semester starts.',
  },
];

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WORKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const FULL_WEEK = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];
const CALENDAR_DAYS = FULL_WEEK;

// ---------------------------------------------------------------------------
// Modal state types
// ---------------------------------------------------------------------------

interface ModalState {
  open: boolean;
  initialBlock?: TimeBlock; // undefined = add mode, defined = edit mode
  defaultType?: 'class' | 'shift'; // only used in add mode
}

interface ImportSummaryState {
  open: boolean;
  importedCount: number;
  conflicts: TimeBlock[];
  reviewItems: ReviewItem[];
  importedSections: Section[];
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type View = 'landing' | 'calendar';

export default function Home() {
  const [view, setView] = useState<View>('landing');
  const [blocks, setBlocks] = useState<TimeBlock[]>(SEED_BLOCKS);
  const [viewDaysMode, setViewDaysMode] = useState<'5day' | '7day'>('7day');
  const [modal, setModal] = useState<ModalState>({ open: false });
  const activeDays = viewDaysMode === '7day' ? FULL_WEEK : WORKDAYS;
  const [importSummary, setImportSummary] = useState<ImportSummaryState>({
    open: false,
    importedCount: 0,
    conflicts: [],
    reviewItems: [],
    importedSections: [],
  });

  const howItWorksRef = useRef<HTMLElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // In-flight request trackers and rollback baselines to prevent race conditions
  const pendingRequests = useRef<
    Map<string | number, { abortController: AbortController; timeoutId?: NodeJS.Timeout }>
  >(new Map());
  const rollbackBaselines = useRef<Map<string | number, TimeBlock>>(new Map());

  // Restore saved blocks from localStorage on mount (guarantees persistence across refresh)
  useEffect(() => {
    try {
      const saved = localStorage.getItem('syncshift_blocks');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setBlocks(parsed);
        }
      }
    } catch (e) {
      console.warn('Could not load blocks from localStorage', e);
    }
  }, []);

  const persistBlocksLocally = useCallback((newBlocks: TimeBlock[]) => {
    try {
      const clean = newBlocks.map(({ isSaving, ...rest }) => rest);
      localStorage.setItem('syncshift_blocks', JSON.stringify(clean));
    } catch (e) {
      console.warn('Could not save blocks to localStorage', e);
    }
  }, []);

  // Compute all blocks including auto-generated conflicts (respecting What-If & Overnight)
  const allBlocks = useMemo(() => detectConflicts(blocks), [blocks]);

  // Compute real-time Visa Hours Compliance & Earnings report (20 hrs limit)
  const visaReport = useMemo(() => calculateWeeklyWorkHours(blocks, 20), [blocks]);

  const scrollToHowItWorks = () => {
    howItWorksRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const triggerFileInput = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // ── .ics File Upload & Parsing Handler ──────────────────────────────────
  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        if (!content) return;

        // 1. Run parser
        const result = parseIcsTimetable(content);

        // 2. Map parsed Sections to TimeBlocks
        const newBlocks = result.sections.map(sectionToTimeBlock);

        // 3. State update: Don't let re-importing wipe out manually added Shifts!
        // Only replace previously-imported Sections:
        // - Keep all shifts (manual & existing)
        // - Keep manual classes (!b.isImported)
        // - Replace imported classes
        setBlocks((prev) => {
          const preservedBlocks = prev.filter(
            (b) => b.type === 'shift' || !b.isImported,
          );
          const nextBlocks = [...preservedBlocks, ...newBlocks];

          // 4. Run conflict check against all blocks (especially shifts)
          const allWithConflicts = detectConflicts(nextBlocks);
          const conflictsFound = allWithConflicts.filter(
            (b) => b.type === 'conflict',
          );

          // 5. Open summary modal with results
          setImportSummary({
            open: true,
            importedCount: result.sections.length,
            conflicts: conflictsFound,
            reviewItems: result.reviewItems,
            importedSections: result.sections,
          });

          // Persist to localStorage
          persistBlocksLocally(nextBlocks);

          return nextBlocks;
        });
      };

      reader.readAsText(file);

      // Reset input value so selecting the same file again triggers onChange
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [persistBlocksLocally],
  );

  // ── Block move handler (supports cross-column newDay + PATCH API & Rollback) ──
  const handleBlockMove = useCallback(
    (
      blockId: string | number,
      newStartTime: string,
      newEndTime: string,
      newDay?: string,
    ) => {
      // 1. Locate current block and record baseline snapshot if not already active
      let previousBlock: TimeBlock | undefined;
      setBlocks((currentBlocks) => {
        const found = currentBlocks.find((b) => b.id === blockId);
        if (found) {
          previousBlock = { ...found };
          if (!rollbackBaselines.current.has(blockId)) {
            rollbackBaselines.current.set(blockId, { ...found });
          }
        }
        return currentBlocks;
      });

      if (!previousBlock) return;

      // 2. Cancel prior in-flight request or debounce timer for this block
      if (pendingRequests.current.has(blockId)) {
        const active = pendingRequests.current.get(blockId)!;
        if (active.timeoutId) clearTimeout(active.timeoutId);
        active.abortController.abort();
        pendingRequests.current.delete(blockId);
      }

      const abortController = new AbortController();

      // 3. Optimistic update in UI state (set isSaving: true)
      setBlocks((prev) => {
        const next = prev.map((b) =>
          b.id === blockId
            ? {
                ...b,
                startTime: newStartTime,
                endTime: newEndTime,
                ...(newDay ? { day: newDay } : {}),
                isSaving: true,
              }
            : b,
        );
        persistBlocksLocally(next);
        return next;
      });

      // 4. Debounce and fire PATCH request (150ms debounce)
      const timeoutId = setTimeout(async () => {
        const token =
          (typeof window !== 'undefined' ? localStorage.getItem('token') : null) ||
          getAuthToken();
        const targetDayStr = newDay || previousBlock?.day || 'Monday';
        const targetDayOfWeek = dayToNumber(targetDayStr);

        try {
          const numericId = Number(blockId);
          if (!isNaN(numericId) && numericId < 1000000000000) {
            const formattedStart =
              newStartTime.length === 5 ? `${newStartTime}:00` : newStartTime;
            const formattedEnd =
              newEndTime.length === 5 ? `${newEndTime}:00` : newEndTime;

            const res = await fetch(`${API_BASE}/blocks/${numericId}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              body: JSON.stringify({
                day_of_week: targetDayOfWeek,
                start_time: formattedStart,
                end_time: formattedEnd,
              }),
              signal: abortController.signal,
            });

            if (res.status === 401) {
              showErrorToast('Session expired. Please log in again.');
              return;
            }

            if (!res.ok) {
              const errJson = await res.json().catch(() => ({}));
              throw new Error(errJson?.error?.message || `Server error (${res.status})`);
            }

            // Also re-fetch conflicts
            const monday = getMondayOfWeek(new Date());
            await fetch(
              `${API_BASE}/conflicts?week_start=${encodeURIComponent(monday)}`,
              {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
              },
            ).catch(() => null);
          }

          // Success: remove isSaving flag
          rollbackBaselines.current.delete(blockId);
          pendingRequests.current.delete(blockId);

          setBlocks((prev) => {
            const next = prev.map((b) =>
              b.id === blockId ? { ...b, isSaving: false } : b,
            );
            persistBlocksLocally(next);
            return next;
          });
        } catch (err: unknown) {
          const error = err as { name?: string };
          if (error?.name === 'AbortError') return;

          console.error(`[handleBlockMove] Failed to persist block #${blockId}:`, err);

          // Rollback to previous baseline snapshot
          const baseline = rollbackBaselines.current.get(blockId) || previousBlock;
          rollbackBaselines.current.delete(blockId);
          pendingRequests.current.delete(blockId);

          if (baseline) {
            setBlocks((prev) => {
              const next = prev.map((b) =>
                b.id === blockId ? { ...baseline, isSaving: false } : b,
              );
              persistBlocksLocally(next);
              return next;
            });
          }

          showErrorToast("Couldn't save move. Please try again.");
        }
      }, 150);

      pendingRequests.current.set(blockId, { abortController, timeoutId });
    },
    [persistBlocksLocally],
  );

  // ── Block resize handler (with API persistence & Rollback) ─────────────
  const handleBlockResize = useCallback(
    (blockId: string | number, newEndTime: string) => {
      let previousBlock: TimeBlock | undefined;
      setBlocks((currentBlocks) => {
        const found = currentBlocks.find((b) => b.id === blockId);
        if (found) previousBlock = { ...found };
        return currentBlocks;
      });

      if (!previousBlock) return;

      // Optimistic update
      setBlocks((prev) => {
        const next = prev.map((b) =>
          b.id === blockId ? { ...b, endTime: newEndTime, isSaving: true } : b,
        );
        persistBlocksLocally(next);
        return next;
      });

      (async () => {
        const token =
          (typeof window !== 'undefined' ? localStorage.getItem('token') : null) ||
          getAuthToken();
        try {
          const numericId = Number(blockId);
          if (!isNaN(numericId) && numericId < 1000000000000) {
            const formattedEnd =
              newEndTime.length === 5 ? `${newEndTime}:00` : newEndTime;
            const res = await fetch(`${API_BASE}/blocks/${numericId}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              body: JSON.stringify({ end_time: formattedEnd }),
            });

            if (!res.ok) {
              const errJson = await res.json().catch(() => ({}));
              throw new Error(errJson?.error?.message || `Server error (${res.status})`);
            }
          }

          setBlocks((prev) => {
            const next = prev.map((b) =>
              b.id === blockId ? { ...b, isSaving: false } : b,
            );
            persistBlocksLocally(next);
            return next;
          });
        } catch (err) {
          console.error(`[handleBlockResize] Failed to persist block #${blockId}:`, err);
          if (previousBlock) {
            setBlocks((prev) => {
              const next = prev.map((b) =>
                b.id === blockId ? { ...previousBlock!, isSaving: false } : b,
              );
              persistBlocksLocally(next);
              return next;
            });
          }
          showErrorToast("Couldn't save resize. Please try again.");
        }
      })();
    },
    [persistBlocksLocally],
  );

  // ── Block click → open edit modal ─────────────────────────────────────
  const handleBlockClick = useCallback((block: TimeBlock) => {
    if (block.type === 'conflict') return; // conflict blocks are computed
    setModal({ open: true, initialBlock: block });
  }, []);

  // ── Modal submit (add or edit) ─────────────────────────────────────────
  const handleModalSubmit = useCallback(
    (block: Omit<TimeBlock, 'id'> & { id?: string | number }) => {
      setBlocks((prev) => {
        let next: TimeBlock[];
        if (block.id != null) {
          // Edit mode — update existing
          next = prev.map((b) =>
            b.id === block.id ? ({ ...b, ...block } as TimeBlock) : b,
          );
        } else {
          // Add mode — assign a stable id
          const newBlock: TimeBlock = { ...block, id: Date.now() } as TimeBlock;
          next = [...prev, newBlock];
        }
        persistBlocksLocally(next);
        return next;
      });
      setModal({ open: false });
    },
    [persistBlocksLocally],
  );

  // ── Block delete ───────────────────────────────────────────────────────
  const handleBlockDelete = useCallback(
    (blockId: string | number) => {
      setBlocks((prev) => {
        const next = prev.filter((b) => b.id !== blockId);
        persistBlocksLocally(next);
        return next;
      });
      setModal({ open: false });
    },
    [persistBlocksLocally],
  );

  const closeModal = useCallback(() => setModal({ open: false }), []);

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      {/* Hidden file input for .ics timetable import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".ics,text/calendar"
        className="hidden"
        onChange={handleFileUpload}
        aria-label="Upload .ics calendar file"
      />

      <AnimatePresence mode="wait">
        {view === 'landing' ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <LandingHero
              onCtaClick={() => setView('calendar')}
              onHowItWorksClick={scrollToHowItWorks}
              onImportClick={triggerFileInput}
            />

            <section
              ref={howItWorksRef}
              id="how-it-works"
              className="w-full max-w-5xl mx-auto px-6 py-20 sm:py-28"
            >
              <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-center mb-4">
                How it works
              </h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 text-center max-w-xl mx-auto mb-14">
                Three steps to a conflict-free semester.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
                {HOW_IT_WORKS_STEPS.map((step) => (
                  <div
                    key={step.number}
                    className="group rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-6 transition-shadow hover:shadow-lg"
                  >
                    <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400 mb-3 font-mono">
                      {step.number}
                    </div>
                    <h3 className="text-sm font-semibold mb-2">{step.title}</h3>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </motion.div>
        ) : (
          <motion.div
            key="calendar"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-4 sm:p-6 lg:p-8"
          >
            <div className="max-w-7xl mx-auto">
              {/* ── Page header ─────────────────────────────────────────── */}
              <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-4">
                  {/* Back button */}
                  <button
                    type="button"
                    onClick={() => setView('landing')}
                    className="inline-flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors"
                    aria-label="Back to landing page"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 19l-7-7m0 0l7-7m-7 7h18"
                      />
                    </svg>
                    Back
                  </button>

                  <div>
                    <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                      Week View
                    </h1>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
                      Fall 2026 · {blocks.filter((b) => b.type === 'class').length} Classes · {blocks.filter((b) => b.type === 'shift').length} Shifts
                    </p>
                  </div>
                </div>

                {/* Right side: legend + action buttons */}
                <div className="flex flex-wrap items-center gap-3">
                  {/* View Days Mode Toggle */}
                  <div className="inline-flex rounded-lg border border-zinc-200 dark:border-zinc-800 p-0.5 bg-zinc-100 dark:bg-zinc-900 text-xs">
                    <button
                      type="button"
                      onClick={() => setViewDaysMode('5day')}
                      className={`px-2.5 py-1 rounded-md transition-colors font-medium ${
                        viewDaysMode === '5day'
                          ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                          : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                    >
                      5 Days
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewDaysMode('7day')}
                      className={`px-2.5 py-1 rounded-md transition-colors font-medium ${
                        viewDaysMode === '7day'
                          ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-sm'
                          : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                    >
                      7 Days
                    </button>
                  </div>

                  {/* Legend */}
                  <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm bg-blue-600" />
                      Class
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm bg-emerald-600" />
                      Shift
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm bg-rose-600" />
                      Conflict
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm border border-dashed border-amber-500 bg-amber-100 dark:bg-amber-950/60" />
                      What-If
                    </span>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2">
                    {/* Import Timetable Button */}
                    <button
                      type="button"
                      onClick={triggerFileInput}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200 transition-colors shadow-sm"
                    >
                      <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                      Import Timetable
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setModal({ open: true, defaultType: 'class' })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                      </svg>
                      Add Class
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setModal({ open: true, defaultType: 'shift' })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white transition-colors shadow-sm"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                      </svg>
                      Add Shift
                    </button>
                  </div>
                </div>
              </div>

              {/* ── Visa Hours Compliance & Earnings Tracker Bar ────────── */}
              <div className="mb-4 px-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/80 backdrop-blur-sm text-xs shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="text-zinc-500 dark:text-zinc-400 font-medium">
                      Visa Work Hours:
                    </span>
                    {visaReport.isViolation ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/70 border border-rose-300 dark:border-rose-900 text-rose-800 dark:text-rose-200 font-semibold animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-rose-600" />
                        Visa Warning: {visaReport.totalHours} / {visaReport.limitHours} hrs worked ({Math.round((visaReport.totalHours - visaReport.limitHours) * 10) / 10}h over limit!)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        Visa Safe: <strong className="font-semibold">{visaReport.totalHours} / {visaReport.limitHours} hrs</strong> ({visaReport.remainingHours}h remaining)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-zinc-500 dark:text-zinc-400">
                    {visaReport.totalEarnings > 0 && (
                      <span>
                        Est. Earnings: <strong className="text-zinc-900 dark:text-zinc-100 font-semibold font-mono">${visaReport.totalEarnings}</strong>/wk
                      </span>
                    )}
                    {blocks.some((b) => b.status === 'tentative') && (
                      <span className="inline-flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                        {blocks.filter((b) => b.status === 'tentative').length} What-If block(s)
                      </span>
                    )}
                  </div>
                </div>

                {/* UKVI / US F-1 Calendar Week Boundary Split Note */}
                {visaReport.complianceNotes && (
                  <div className="w-full mt-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 flex items-center gap-2 text-[11px] text-purple-700 dark:text-purple-300">
                    <span className="font-semibold px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-950/70 border border-purple-300 dark:border-purple-800">
                      UKVI / F-1 Boundary Rule
                    </span>
                    <span>{visaReport.complianceNotes}</span>
                  </div>
                )}
              </div>

              {/* ── Calendar ────────────────────────────────────────────── */}
              <div style={{ height: '75vh' }}>
                <CalendarWeekView
                  blocks={allBlocks}
                  startHour={7}
                  endHour={24}
                  days={activeDays}
                  onBlockClick={handleBlockClick}
                  onBlockMove={handleBlockMove}
                  onBlockResize={handleBlockResize}
                  snapMinutes={15}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Block form modal (Add / Edit) ─────────────────────────────────── */}
      <AnimatePresence>
        {modal.open && (
          <BlockFormModal
            initialBlock={modal.initialBlock}
            defaultType={modal.defaultType}
            existingBlocks={blocks}
            days={CALENDAR_DAYS}
            onSubmit={handleModalSubmit}
            onDelete={handleBlockDelete}
            onClose={closeModal}
          />
        )}
      </AnimatePresence>

      {/* ── Timetable Import Summary Modal ────────────────────────────────── */}
      <AnimatePresence>
        {importSummary.open && (
          <ImportSummaryModal
            open={importSummary.open}
            onClose={() =>
              setImportSummary((prev) => ({ ...prev, open: false }))
            }
            onGoToCalendar={() => {
              setImportSummary((prev) => ({ ...prev, open: false }));
              setView('calendar');
            }}
            importedCount={importSummary.importedCount}
            conflicts={importSummary.conflicts}
            reviewItems={importSummary.reviewItems}
            importedSections={importSummary.importedSections}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
