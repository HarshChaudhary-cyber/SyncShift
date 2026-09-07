'use client';

import React, { useState, useRef } from 'react';
import { api, IcsPreviewItem } from '@/lib/api';
import { useCalendar } from '@/context/CalendarContext';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onToast: (message: string) => void;
}

const DAY_NAMES: Record<number, string> = {
  0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat',
};

export default function ImportModal({ isOpen, onClose, onToast }: ImportModalProps) {
  const { refreshWeek } = useCalendar();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewBlocks, setPreviewBlocks] = useState<IcsPreviewItem[]>([]);
  const [unmatchedCount, setUnmatchedCount] = useState<number>(0);
  const [conflictsDetected, setConflictsDetected] = useState<number>(0);

  if (!isOpen) return null;

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.previewIcs(file);
      setPreviewBlocks(res.preview || []);
      setUnmatchedCount(res.unmatched ? res.unmatched.length : 0);
      setConflictsDetected(0);
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to parse .ics file');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (previewBlocks.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const payload = {
        preview_blocks: previewBlocks.map((b) => ({
          title: b.title,
          day_of_week: b.day_of_week,
          start_time: b.start_time,
          end_time: b.end_time,
        })),
      };
      const res = await api.confirmIcs(payload);
      await refreshWeek();
      onToast(`${res.created_count || previewBlocks.length} classes imported successfully!`);
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to import timetable');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="w-full max-w-[420px] bg-neutral-900 border border-neutral-800 rounded-xl p-5 shadow-2xl text-neutral-100">
        <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
          <h2 className="text-base font-semibold">Import Timetable (.ics)</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-white cursor-pointer">✕</button>
        </div>

        {error && (
          <div className="mt-3 p-2 bg-rose-950/60 border border-rose-600 rounded text-xs text-rose-200">
            {error}
          </div>
        )}

        <div className="mt-4">
          <input ref={fileInputRef} type="file" accept=".ics,text/calendar" onChange={handleFileChange} className="hidden" />
          {previewBlocks.length === 0 ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-neutral-700 hover:border-blue-500/80 rounded-lg p-6 text-center cursor-pointer transition-colors"
            >
              <div className="text-2xl mb-2">📅</div>
              <p className="text-xs font-medium text-neutral-200">Choose .ics file</p>
              <p className="text-[11px] text-neutral-400 mt-1">Export from Canvas, Google Calendar, or Outlook</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs bg-neutral-950 p-2.5 rounded-lg border border-neutral-800">
                <span className="text-neutral-300">
                  <strong>{previewBlocks.length}</strong> classes found
                </span>
                {conflictsDetected > 0 && (
                  <span className="text-rose-400 font-medium">
                    ⚠️ {conflictsDetected} conflict{conflictsDetected > 1 ? 's' : ''}
                  </span>
                )}
              </div>

              {unmatchedCount > 0 && (
                <div className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded text-xs text-amber-300">
                  ⚠️ {unmatchedCount} events need manual review
                </div>
              )}

              <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 text-xs">
                {previewBlocks.map((block, idx) => (
                  <div key={idx} className="p-2 bg-neutral-950/80 border border-neutral-800/80 rounded flex justify-between items-center">
                    <div>
                      <p className="font-medium text-neutral-200">{block.title}</p>
                      <p className="text-[11px] text-neutral-400">
                        {DAY_NAMES[block.day_of_week] || 'Day'} · {block.start_time.slice(0, 5)} - {block.end_time.slice(0, 5)}
                      </p>
                    </div>
                    {block.course_code && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-blue-900/50 text-blue-300 rounded">
                        {block.course_code}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-between items-center pt-4 mt-3 border-t border-neutral-800">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="text-xs text-neutral-400 hover:text-neutral-200 underline cursor-pointer"
          >
            {previewBlocks.length > 0 ? 'Pick another file' : ''}
          </button>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded text-xs cursor-pointer">
              Cancel
            </button>
            <button
              type="button"
              disabled={previewBlocks.length === 0 || loading}
              onClick={handleConfirm}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-xs font-medium text-white cursor-pointer"
            >
              {loading ? 'Importing...' : 'Import'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
