'use client';

import React, { useState } from 'react';
import { api, FilePreviewItem } from '@/lib/api';

export default function AssistantTimetableUpload({ onDone, onClose }: {
  onDone: (message: string) => void; onClose: () => void;
}) {
  const [items, setItems] = useState<FilePreviewItem[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [automatic, setAutomatic] = useState(true);

  async function save(rows: FilePreviewItem[]) {
    const result = await api.confirmFile({ preview_blocks: rows.map(row => ({
      title: row.title, day_of_week: row.day_of_week, start_time: row.start_time,
      end_time: row.end_time, location: row.location, is_recurring: row.is_recurring ?? true,
      recurrence_interval: row.recurrence_interval ?? 1,
      effective_from: row.effective_from ?? undefined, effective_until: row.effective_until ?? undefined,
    })) });
    window.dispatchEvent(new CustomEvent('syncshift:schedule-updated'));
    onDone(`Imported ${result.created_count} timetable events into your calendar. ${result.conflicts_detected} conflicts detected. Open Calendar to review or edit the events.`);
  }

  async function upload(file?: File) {
    if (!file) return;
    setError(''); setItems([]); setSelected([]); setBusy(true);
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('Choose a file smaller than 20 MB.');
      const response = await api.previewFile(file);
      if (!response.preview.length) throw new Error(response.message || 'No schedule entries found. Try a clearer file.');
      const clean = response.preview.every(row => row.confidence === 'high' && row.status === 'valid' && !row.is_duplicate && !row.has_conflict);
      if (automatic && clean) {
        await save(response.preview);
      } else {
        setItems(response.preview);
        setSelected(response.preview.flatMap((row, i) => row.status === 'valid' && !row.is_duplicate ? [i] : []));
      }
    } catch (e) { setError(e instanceof Error ? e.message : 'Import failed.'); }
    finally { setBusy(false); }
  }

  return <section aria-label="Import timetable in assistant" className="p-4 border-b border-indigo-300 dark:border-indigo-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white space-y-3 max-h-80 overflow-y-auto">
    <div className="flex justify-between"><strong>Attach a timetable</strong><button type="button" onClick={onClose} disabled={busy} aria-label="Close timetable upload">✕</button></div>
    <p className="text-xs">PDF, ICS, CSV, Excel, Word, PowerPoint, TXT, JPG, PNG or WebP · up to 20 MB. Complex documents may use the configured AI service.</p>
    <label className="flex gap-2 text-xs"><input type="checkbox" checked={automatic} disabled={busy} onChange={e => setAutomatic(e.target.checked)} />Automatically import clear entries when no conflicts or duplicates are found</label>
    <input aria-label="Timetable file" type="file" disabled={busy} accept=".pdf,.ics,.ical,.csv,.xlsx,.xls,.doc,.docx,.pptx,.txt,.jpg,.jpeg,.png,.webp" onChange={e => {void upload(e.target.files?.[0]); e.target.value = '';}} className="w-full text-xs" />
    {busy && <p role="status">Reading and checking your timetable…</p>}
    {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
    {!!items.length && <>
      <p className="text-xs">Review these entries. Uncertain entries and conflicts require your selection. Use Calendar → Import Timetable if you need to correct extracted details first.</p>
      {items.map((item, i) => <label key={i} className="flex items-start gap-2 border rounded p-2 text-xs">
        <input type="checkbox" disabled={busy || item.day_of_week < 0 || !item.start_time || !item.end_time || item.is_duplicate} checked={selected.includes(i)} onChange={e => setSelected(prev => e.target.checked ? [...prev, i] : prev.filter(n => n !== i))} />
        <span>{item.title} — {item.day_name} {item.start_time}–{item.end_time}<br />{item.issues?.join(' · ') || item.status}</span>
      </label>)}
      <button type="button" disabled={busy || !selected.length} className="rounded px-3 py-2 bg-indigo-600 text-white disabled:opacity-50" onClick={async () => {
        setBusy(true); setError('');
        try { await save(items.filter((_, i) => selected.includes(i))); }
        catch (e) { setError(e instanceof Error ? e.message : 'Could not save timetable.'); }
        finally { setBusy(false); }
      }}>Import {selected.length} selected events</button>
    </>}
  </section>;
}
