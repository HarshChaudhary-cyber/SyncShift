'use client';

import React, { useState } from 'react';
import { api, FilePreviewItem } from '@/lib/api';
import { XMarkIcon, ArrowUpTrayIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

export default function AssistantTimetableUpload({
  onDone,
  onClose,
}: {
  onDone: (message: string) => void;
  onClose: () => void;
}) {
  const [items, setItems] = useState<FilePreviewItem[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [automatic, setAutomatic] = useState(true);

  async function save(rows: FilePreviewItem[]) {
    const result = await api.confirmFile({
      preview_blocks: rows.map((row) => ({
        title: row.title,
        day_of_week: row.day_of_week,
        start_time: row.start_time,
        end_time: row.end_time,
        location: row.location,
        is_recurring: row.is_recurring ?? true,
        recurrence_interval: row.recurrence_interval ?? 1,
        effective_from: row.effective_from ?? undefined,
        effective_until: row.effective_until ?? undefined,
      })),
    });
    window.dispatchEvent(new CustomEvent('syncshift:schedule-updated'));
    onDone(
      `Imported ${result.created_count} timetable events into your calendar. ${result.conflicts_detected} conflicts detected. Open Calendar to review or edit the events.`
    );
  }

  async function upload(file?: File) {
    if (!file) return;
    setError('');
    setItems([]);
    setSelected([]);
    setBusy(true);
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('Choose a file smaller than 20 MB.');
      const response = await api.previewFile(file);
      if (!response.preview.length)
        throw new Error(response.message || 'No schedule entries found. Try a clearer file.');
      const clean = response.preview.every(
        (row) =>
          row.confidence === 'high' &&
          row.status === 'valid' &&
          !row.is_duplicate &&
          !row.has_conflict
      );
      if (automatic && clean) {
        await save(response.preview);
      } else {
        setItems(response.preview);
        setSelected(
          response.preview.flatMap((row, i) =>
            row.status === 'valid' && !row.is_duplicate ? [i] : []
          )
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-label="Import timetable in assistant"
      className="p-4 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] text-[var(--text-primary)] space-y-3 max-h-80 overflow-y-auto custom-scrollbar"
    >
      <div className="flex items-center justify-between">
        <strong className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <ArrowUpTrayIcon className="w-4 h-4 text-indigo-500" aria-hidden="true" />
          Attach a timetable
        </strong>
        <button
          type="button"
          onClick={onClose}
          disabled={busy}
          aria-label="Close timetable upload"
          className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition cursor-pointer"
        >
          <XMarkIcon className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
        PDF, ICS, CSV, Excel, Word, PowerPoint, TXT, JPG, PNG or WebP · up to 20 MB. Complex documents may use the configured AI service.
      </p>

      <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
        <input
          type="checkbox"
          checked={automatic}
          disabled={busy}
          onChange={(e) => setAutomatic(e.target.checked)}
          className="rounded border-[var(--border-color)] text-indigo-600 focus:ring-indigo-500"
        />
        <span>Automatically import clear entries when no conflicts or duplicates are found</span>
      </label>

      <div>
        <input
          aria-label="Timetable file"
          type="file"
          disabled={busy}
          accept=".pdf,.ics,.ical,.csv,.xlsx,.xls,.doc,.docx,.pptx,.txt,.jpg,.jpeg,.png,.webp"
          onChange={(e) => {
            void upload(e.target.files?.[0]);
            e.target.value = '';
          }}
          className="w-full text-xs text-[var(--text-secondary)] file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-medium file:bg-[var(--bg-card)] file:text-[var(--text-primary)] hover:file:bg-[var(--border-color)]/30 cursor-pointer"
        />
      </div>

      {busy && (
        <div role="status" className="flex items-center gap-2 text-xs text-indigo-600 dark:text-indigo-400 font-medium">
          <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
          <span>Reading and checking your timetable…</span>
        </div>
      )}

      {error && (
        <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 font-medium">
          {error}
        </p>
      )}

      {Boolean(items.length) && (
        <div className="space-y-2 pt-1 border-t border-[var(--border-color)]">
          <p className="text-[11px] text-[var(--text-muted)]">
            Review these entries. Uncertain entries and conflicts require your selection. Use Calendar → Import Timetable if you need to correct extracted details first.
          </p>
          <div className="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar">
            {items.map((item, i) => (
              <label
                key={i}
                className="flex items-start gap-2 border border-[var(--border-color)] rounded-lg p-2 text-xs bg-[var(--bg-card)] cursor-pointer"
              >
                <input
                  type="checkbox"
                  disabled={
                    busy ||
                    item.day_of_week < 0 ||
                    !item.start_time ||
                    !item.end_time ||
                    item.is_duplicate
                  }
                  checked={selected.includes(i)}
                  onChange={(e) =>
                    setSelected((prev) =>
                      e.target.checked ? [...prev, i] : prev.filter((n) => n !== i)
                    )
                  }
                  className="mt-0.5 rounded border-[var(--border-color)] text-indigo-600 focus:ring-indigo-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[var(--text-primary)] truncate">
                    {item.title} — {item.day_name} {item.start_time}–{item.end_time}
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    {item.issues?.join(' · ') || item.status}
                  </div>
                </div>
              </label>
            ))}
          </div>

          <button
            type="button"
            disabled={busy || !selected.length}
            className="w-full rounded-lg px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-50 transition shadow-xs cursor-pointer"
            onClick={async () => {
              setBusy(true);
              setError('');
              try {
                await save(items.filter((_, i) => selected.includes(i)));
              } catch (e) {
                setError(e instanceof Error ? e.message : 'Could not save timetable.');
              } finally {
                setBusy(false);
              }
            }}
          >
            Import {selected.length} selected events
          </button>
        </div>
      )}
    </section>
  );
}
