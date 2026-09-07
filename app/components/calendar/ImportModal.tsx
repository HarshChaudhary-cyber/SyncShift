'use client';

import React, { useState, useRef } from 'react';
import { api, FilePreviewItem, IcsConfirmPayload } from '@/lib/api';
import { useCalendar } from '@/context/CalendarContext';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onToast: (message: string) => void;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ACCEPT = '.ics,.pdf,.docx,.pptx,.txt,.csv,.jpg,.jpeg,.png,text/calendar,application/pdf,image/*';

const DAY_NAMES: Record<number, string> = {
  0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun',
};

const IMAGE_EXTS = new Set(['.jpg', '.jpeg', '.png']);

function getExt(name: string): string {
  const idx = name.lastIndexOf('.');
  return idx !== -1 ? name.slice(idx).toLowerCase() : '';
}

function isImageFile(name: string) {
  return IMAGE_EXTS.has(getExt(name));
}

// ─── Loading state label ──────────────────────────────────────────────────────

type LoadingPhase = 'idle' | 'reading' | 'done';

// ─── Component ────────────────────────────────────────────────────────────────

export default function ImportModal({ isOpen, onClose, onToast }: ImportModalProps) {
  const { refreshWeek } = useCalendar();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>('idle');
  const [error, setError] = useState<string | null>(null);
  const [previewBlocks, setPreviewBlocks] = useState<FilePreviewItem[]>([]);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [isConfirming, setIsConfirming] = useState(false);

  if (!isOpen) return null;

  // ─── Reset ─────────────────────────────────────────────────────────────────

  const resetState = () => {
    setError(null);
    setPreviewBlocks([]);
    setCheckedIds(new Set());
    setEmptyMessage(null);
    setSelectedFileName('');
    setLoadingPhase('idle');
    setIsConfirming(false);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  // ─── File upload ────────────────────────────────────────────────────────────

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    resetState();
    setSelectedFileName(file.name);
    setLoadingPhase('reading');

    try {
      // Always route through the new unified endpoint (it handles ICS too)
      const res = await api.previewFile(file);

      const blocks = res.preview ?? [];

      // Default checked = rows that have parseable start + valid day
      const defaultChecked = new Set<string>(
        blocks
          .filter(b => b.start_time && b.start_time !== '' && b.day_of_week >= 0)
          .map(b => b.temp_id ?? `${b.day_of_week}-${b.start_time}`)
      );

      setPreviewBlocks(blocks);
      setCheckedIds(defaultChecked);
      setEmptyMessage(res.message ?? null);
      setLoadingPhase('done');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to parse file';
      setError(msg);
      setLoadingPhase('idle');
    } finally {
      // Reset the input so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // ─── Checkbox ──────────────────────────────────────────────────────────────

  const toggleChecked = (id: string) => {
    setCheckedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    const selectableIds = previewBlocks
      .filter(b => b.start_time && b.start_time !== '' && b.day_of_week >= 0)
      .map(b => b.temp_id ?? `${b.day_of_week}-${b.start_time}`);

    if (selectableIds.every(id => checkedIds.has(id))) {
      setCheckedIds(new Set());
    } else {
      setCheckedIds(new Set(selectableIds));
    }
  };

  // ─── Confirm import ─────────────────────────────────────────────────────────

  const handleConfirm = async () => {
    const selected = previewBlocks.filter(b => {
      const id = b.temp_id ?? `${b.day_of_week}-${b.start_time}`;
      return checkedIds.has(id) && b.start_time && b.day_of_week >= 0;
    });

    if (selected.length === 0) return;

    setIsConfirming(true);
    setError(null);

    try {
      const payload: IcsConfirmPayload = {
        preview_blocks: selected.map(b => ({
          title: b.title,
          day_of_week: b.day_of_week,
          start_time: b.start_time,
          end_time: b.end_time,
          location: b.location ?? null,
        })),
      };

      const res = await api.confirmFile(payload);
      await refreshWeek();

      const count = res.created_count ?? selected.length;
      const conflicts = res.conflicts_detected ?? 0;
      const conflictNote = conflicts > 0 ? ` (${conflicts} conflict${conflicts > 1 ? 's' : ''} detected)` : '';
      onToast(`${count} class${count !== 1 ? 'es' : ''} imported successfully!${conflictNote}`);
      handleClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to import timetable');
    } finally {
      setIsConfirming(false);
    }
  };

  // ─── Derived state ──────────────────────────────────────────────────────────

  const selectableBlocks = previewBlocks.filter(
    b => b.start_time && b.start_time !== '' && b.day_of_week >= 0
  );
  const checkedCount = selectableBlocks.filter(
    b => checkedIds.has(b.temp_id ?? `${b.day_of_week}-${b.start_time}`)
  ).length;
  const lowConfidenceCount = previewBlocks.filter(b => b.confidence === 'low').length;
  const isImage = selectedFileName ? isImageFile(selectedFileName) : false;

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="w-full max-w-[460px] bg-neutral-900 border border-neutral-800 rounded-xl p-5 shadow-2xl text-neutral-100 flex flex-col gap-4">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
          <div>
            <h2 className="text-base font-semibold">Import Timetable</h2>
            <p className="text-[11px] text-neutral-400 mt-0.5">
              Supported: ICS · PDF · DOCX · PPTX · TXT · CSV · JPG · PNG
            </p>
          </div>
          <button onClick={handleClose} className="text-neutral-400 hover:text-white cursor-pointer text-lg leading-none">✕</button>
        </div>

        {/* Error */}
        {error && (
          <div className="p-2.5 bg-rose-950/60 border border-rose-600 rounded text-xs text-rose-200 flex gap-2">
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* Upload zone / Preview */}
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            onChange={handleFileChange}
            className="hidden"
          />

          {/* ── Upload drop zone (when no preview yet) ── */}
          {loadingPhase === 'idle' && previewBlocks.length === 0 && !emptyMessage && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-neutral-700 hover:border-blue-500/80 rounded-lg p-7 text-center cursor-pointer transition-colors group"
            >
              <div className="text-3xl mb-2">📁</div>
              <p className="text-xs font-medium text-neutral-200 group-hover:text-white transition-colors">
                Choose a file to import
              </p>
              <p className="text-[11px] text-neutral-500 mt-1">
                ICS · PDF · DOCX · PPTX · TXT · CSV · JPG · PNG
              </p>
              <p className="text-[11px] text-neutral-600 mt-1">
                Export from Canvas, Outlook, or take a photo of your timetable
              </p>
            </div>
          )}

          {/* ── Reading / parsing ── */}
          {loadingPhase === 'reading' && (
            <div className="flex flex-col items-center justify-center py-10 gap-3 text-neutral-400">
              <div className="w-6 h-6 border-2 border-neutral-600 border-t-blue-500 rounded-full animate-spin" />
              <p className="text-xs">Reading file…</p>
              {isImage && (
                <p className="text-[11px] text-neutral-500 max-w-[220px] text-center">
                  Running OCR on image — best results with a clear, well-lit screenshot
                </p>
              )}
            </div>
          )}

          {/* ── Empty result message ── */}
          {loadingPhase === 'done' && emptyMessage && previewBlocks.length === 0 && (
            <div className="flex flex-col items-center justify-center py-6 gap-3 text-center">
              <div className="text-3xl">🔍</div>
              <p className="text-sm text-neutral-300 font-medium">No timetable found</p>
              <p className="text-xs text-neutral-500 max-w-[300px]">{emptyMessage}</p>
              <button
                onClick={() => { resetState(); fileInputRef.current?.click(); }}
                className="mt-2 text-xs text-blue-400 hover:text-blue-300 underline cursor-pointer"
              >
                Try another file
              </button>
            </div>
          )}

          {/* ── Preview list ── */}
          {previewBlocks.length > 0 && (
            <div className="space-y-3">
              {/* Summary bar */}
              <div className="flex items-center justify-between text-xs bg-neutral-950 p-2.5 rounded-lg border border-neutral-800 gap-2">
                <span className="text-neutral-300">
                  <strong className="text-white">{previewBlocks.length}</strong> event{previewBlocks.length !== 1 ? 's' : ''} found
                  {selectedFileName && <span className="text-neutral-500 ml-1 truncate max-w-[120px] inline-block align-bottom">{selectedFileName}</span>}
                </span>
                <span className="text-neutral-400">
                  <strong className="text-white">{checkedCount}</strong> selected
                </span>
              </div>

              {/* Image hint */}
              {isImage && (
                <div className="px-3 py-2 bg-blue-500/10 border border-blue-500/30 rounded text-[11px] text-blue-300">
                  📷 Best results: clear screenshot, timetable fills most of the frame
                </div>
              )}

              {/* Low-confidence warning */}
              {lowConfidenceCount > 0 && (
                <div className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded text-xs text-amber-300">
                  ⚠ {lowConfidenceCount} event{lowConfidenceCount > 1 ? 's' : ''} flagged low-confidence — verify before importing
                </div>
              )}

              {/* Select all toggle */}
              {selectableBlocks.length > 1 && (
                <button
                  onClick={toggleAll}
                  className="text-[11px] text-neutral-400 hover:text-neutral-200 underline cursor-pointer"
                >
                  {checkedCount === selectableBlocks.length ? 'Deselect all' : 'Select all'}
                </button>
              )}

              {/* Block rows */}
              <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1 text-xs">
                {previewBlocks.map((block, idx) => {
                  const id = block.temp_id ?? `${block.day_of_week}-${block.start_time}-${idx}`;
                  const selectable = block.start_time !== '' && block.day_of_week >= 0;
                  const checked = checkedIds.has(id);
                  const isLow = block.confidence === 'low';
                  const dayLabel = block.day_of_week >= 0 ? (DAY_NAMES[block.day_of_week] ?? '?') : '?';
                  const timeLabel = block.start_time
                    ? `${block.start_time.slice(0, 5)}${block.end_time ? ' – ' + block.end_time.slice(0, 5) : ''}`
                    : 'Time unknown';

                  return (
                    <div
                      key={id}
                      onClick={() => selectable && toggleChecked(id)}
                      className={`
                        p-2 rounded border flex gap-2 items-start transition-colors
                        ${selectable ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}
                        ${checked
                          ? isLow
                            ? 'bg-amber-950/30 border-amber-700/50'
                            : 'bg-blue-950/30 border-blue-700/50'
                          : 'bg-neutral-950/80 border-neutral-800/80 hover:border-neutral-700'
                        }
                      `}
                    >
                      {/* Checkbox */}
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={!selectable}
                        onChange={() => selectable && toggleChecked(id)}
                        onClick={e => e.stopPropagation()}
                        className="mt-0.5 accent-blue-500 cursor-pointer shrink-0"
                      />

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <p className={`font-medium truncate ${isLow ? 'text-amber-200' : 'text-neutral-200'}`}>
                            {block.title}
                          </p>
                          {isLow && (
                            <span className="shrink-0 text-[10px] px-1.5 py-0.5 bg-amber-900/50 text-amber-300 rounded-full border border-amber-700/40">
                              ⚠ low confidence
                            </span>
                          )}
                          {block.course_code && (
                            <span className="shrink-0 text-[10px] px-1.5 py-0.5 bg-blue-900/50 text-blue-300 rounded-full">
                              {block.course_code}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-neutral-400 mt-0.5">
                          {dayLabel} · {timeLabel}
                          {block.location && <span className="text-neutral-500"> · {block.location}</span>}
                        </p>
                        {!selectable && (
                          <p className="text-[10px] text-rose-400 mt-0.5">Could not parse time — add manually</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between items-center pt-3 border-t border-neutral-800">
          <button
            type="button"
            onClick={() => { resetState(); fileInputRef.current?.click(); }}
            className="text-xs text-neutral-400 hover:text-neutral-200 underline cursor-pointer"
          >
            {previewBlocks.length > 0 || emptyMessage ? 'Pick another file' : ''}
          </button>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded text-xs cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={checkedCount === 0 || isConfirming}
              onClick={handleConfirm}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-xs font-medium text-white cursor-pointer min-w-[80px]"
            >
              {isConfirming
                ? 'Importing…'
                : checkedCount > 0
                  ? `Import ${checkedCount}`
                  : 'Import'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
