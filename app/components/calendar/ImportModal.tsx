'use client';

import React, { useState, useRef } from 'react';
import { api, FilePreviewItem, FilePreviewResponse, IcsConfirmPayload } from '@/lib/api';
import { useCalendar } from '@/context/CalendarContext';
import DatePicker from '@/components/ui/DatePicker';
import CustomSelect from '@/components/ui/CustomSelect';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onToast: (message: string) => void;
}

const ACCEPT = '.pdf,.docx,.pptx,.txt,.csv,.jpg,.jpeg,.png,.webp,.ics';
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20MB
const ALLOWED_EXTS = ['.pdf', '.docx', '.pptx', '.txt', '.csv', '.jpg', '.jpeg', '.png', '.webp', '.ics'];

const DAY_ORDER = [0, 1, 2, 3, 4, 5, 6, -1];
const DAY_LABELS: Record<number, string> = {
  0: 'Monday',
  1: 'Tuesday',
  2: 'Wednesday',
  3: 'Thursday',
  4: 'Friday',
  5: 'Saturday',
  6: 'Sunday',
  [-1]: 'Unassigned Day',
};

type ModalStep = 'upload' | 'processing' | 'preview' | 'confirm' | 'success' | 'error';

interface ProcessingChecklistItem {
  label: string;
  status: 'pending' | 'in_progress' | 'completed';
}

export default function ImportModal({ isOpen, onClose, onToast }: ImportModalProps) {
  const { refreshWeek } = useCalendar();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Flow step
  const [currentStep, setCurrentStep] = useState<ModalStep>('upload');
  
  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [fileValidationError, setFileValidationError] = useState<string | null>(null);

  // Processing checklist
  const [checklist, setChecklist] = useState<ProcessingChecklistItem[]>([
    { label: 'File uploaded', status: 'completed' },
    { label: 'Document recognized', status: 'in_progress' },
    { label: 'Extracting schedule', status: 'pending' },
    { label: 'Validating events', status: 'pending' },
    { label: 'Checking conflicts', status: 'pending' },
  ]);

  // Preview state
  const [previewBlocks, setPreviewBlocks] = useState<FilePreviewItem[]>([]);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [totalFound, setTotalFound] = useState<number>(0);
  const [validCount, setValidCount] = useState<number>(0);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [duplicateCount, setDuplicateCount] = useState<number>(0);
  const [conflictCount, setConflictCount] = useState<number>(0);
  const [effectiveFrom, setEffectiveFrom] = useState<string | null>(() => new Date().toISOString().slice(0, 10));
  const [effectiveUntil, setEffectiveUntil] = useState<string | null>(null);

  // Inline editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{
    title: string;
    day_of_week: number;
    start_time: string;
    end_time: string;
    location: string;
    course_code: string;
  }>({
    title: '',
    day_of_week: 0,
    start_time: '',
    end_time: '',
    location: '',
    course_code: '',
  });

  // Confirm / Persistence state
  const [isConfirming, setIsConfirming] = useState(false);
  const [importSummary, setImportSummary] = useState<{ createdCount: number; conflictsDetected: number }>({
    createdCount: 0,
    conflictsDetected: 0,
  });

  // Error state
  const [errorDetails, setErrorDetails] = useState<{ title: string; message: string }>({
    title: 'Unable to read timetable',
    message: 'Please verify the file format or try an ICS export.',
  });

  const resetState = () => {
    setCurrentStep('upload');
    setSelectedFile(null);
    setIsDragOver(false);
    setFileValidationError(null);
    setPreviewBlocks([]);
    setCheckedIds(new Set());
    setTotalFound(0);
    setValidCount(0);
    setReviewCount(0);
    setDuplicateCount(0);
    setConflictCount(0);
    setEditingId(null);
    setIsConfirming(false);
    setImportSummary({ createdCount: 0, conflictsDetected: 0 });
    setEffectiveFrom(new Date().toISOString().slice(0, 10));
    setEffectiveUntil(null);
    setChecklist([
      { label: 'File uploaded', status: 'completed' },
      { label: 'Document recognized', status: 'in_progress' },
      { label: 'Extracting schedule', status: 'pending' },
      { label: 'Validating events', status: 'pending' },
      { label: 'Checking conflicts', status: 'pending' },
    ]);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const getFileExt = (name: string): string => {
    const idx = name.lastIndexOf('.');
    return idx !== -1 ? name.slice(idx).toLowerCase() : '';
  };

  // ─── Step 1: Pre-upload Client-side Validation ─────────────────────────────
  const validateSelectedFile = (file: File): string | null => {
    if (!file || file.size === 0) {
      return 'The selected file is empty. Please choose a valid timetable file.';
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return 'File is too large. Please choose a timetable file under 20MB.';
    }
    const ext = getFileExt(file.name);
    if (!ALLOWED_EXTS.includes(ext)) {
      return 'Unsupported file type. Supported: PDF, DOCX, PPTX, image (JPG, PNG), TXT, ICS.';
    }
    if (['.doc', '.ppt', '.xls', '.xlsx'].includes(ext)) {
      return `Legacy format '${ext}' is not supported. Please save the file as .docx or .pptx.`;
    }
    return null;
  };

  const processUploadedFile = async (file: File) => {
    const validationErr = validateSelectedFile(file);
    if (validationErr) {
      setFileValidationError(validationErr);
      return;
    }

    setFileValidationError(null);
    setSelectedFile(file);
    setCurrentStep('processing');

    // Progressive checklist cadence (simulating real pipeline stages without fake percentages)
    const t1 = setTimeout(() => {
      setChecklist([
        { label: 'File uploaded', status: 'completed' },
        { label: 'Document recognized', status: 'completed' },
        { label: 'Extracting schedule', status: 'in_progress' },
        { label: 'Validating events', status: 'pending' },
        { label: 'Checking conflicts', status: 'pending' },
      ]);
    }, 600);

    const t2 = setTimeout(() => {
      setChecklist([
        { label: 'File uploaded', status: 'completed' },
        { label: 'Document recognized', status: 'completed' },
        { label: 'Extracting schedule', status: 'completed' },
        { label: 'Validating events', status: 'in_progress' },
        { label: 'Checking conflicts', status: 'pending' },
      ]);
    }, 1500);

    try {
      const res: FilePreviewResponse = await api.previewFile(file);
      clearTimeout(t1);
      clearTimeout(t2);

      // Finalize checklist
      setChecklist([
        { label: 'File uploaded', status: 'completed' },
        { label: 'Document recognized', status: 'completed' },
        { label: 'Extracting schedule', status: 'completed' },
        { label: 'Validating events', status: 'completed' },
        { label: 'Checking conflicts', status: 'completed' },
      ]);

      const blocks = res.preview ?? [];
      if (blocks.length === 0) {
        setErrorDetails({
          title: 'No timetable detected',
          message:
            res.message ||
            "We couldn't detect recurring class schedules in this file. Try a clearer screenshot, PDF, or an .ics calendar file.",
        });
        setCurrentStep('error');
        return;
      }

      setPreviewBlocks(blocks);
      setTotalFound(res.total_found ?? blocks.length);
      setValidCount(res.valid_count ?? blocks.filter(b => (b.status ?? 'valid') === 'valid').length);
      setReviewCount(res.review_count ?? blocks.filter(b => b.status === 'needs_review').length);
      setDuplicateCount(res.duplicate_count ?? blocks.filter(b => b.is_duplicate).length);
      setConflictCount(res.conflict_count ?? blocks.filter(b => b.has_conflict).length);

      // Check all valid or conflict items by default; leave duplicates and low confidence unchecked
      const defaultChecked = new Set<string>();
      blocks.forEach((b, idx) => {
        const id = b.temp_id || `item-${idx}`;
        if (!b.is_duplicate && b.start_time && b.day_of_week >= 0 && b.confidence !== 'low') {
          defaultChecked.add(id);
        }
      });
      setCheckedIds(defaultChecked);

      // Transition smoothly to preview
      setTimeout(() => {
        setCurrentStep('preview');
      }, 400);
    } catch (err: unknown) {
      clearTimeout(t1);
      clearTimeout(t2);
      const msg = err instanceof Error ? err.message : String(err);
      setErrorDetails({
        title: "We couldn't process this file.",
        message: msg.includes('422') || msg.toLowerCase().includes('timetable')
          ? "The timetable parser could not identify classes in this file. Please verify the format or try an ICS export."
          : msg,
      });
      setCurrentStep('error');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processUploadedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processUploadedFile(file);
  };

  // ─── Step 5/6: Preview & Item Selection / Exclusion ─────────────────────────
  const toggleChecked = (id: string) => {
    setCheckedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    const validItems = previewBlocks
      .filter(b => b.start_time && b.day_of_week >= 0)
      .map((b, idx) => b.temp_id || `item-${idx}`);

    if (validItems.every(id => checkedIds.has(id))) {
      setCheckedIds(new Set());
    } else {
      setCheckedIds(new Set(validItems));
    }
  };

  // ─── Inline Item Editing ───────────────────────────────────────────────────
  const startEditing = (block: FilePreviewItem, id: string) => {
    setEditingId(id);
    setEditForm({
      title: block.title,
      day_of_week: block.day_of_week,
      start_time: block.start_time,
      end_time: block.end_time,
      location: block.location || '',
      course_code: block.course_code || '',
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
  };

  const saveEditing = (id: string) => {
    setPreviewBlocks(prev =>
      prev.map((item, idx) => {
        const itemId = item.temp_id || `item-${idx}`;
        if (itemId !== id) return item;

        const fixedStartTime = editForm.start_time.trim();
        const fixedEndTime = editForm.end_time.trim();
        const fixedDay = editForm.day_of_week;

        const updatedIssues = (item.issues ?? []).filter(
          iss =>
            !iss.toLowerCase().includes('day') &&
            !iss.toLowerCase().includes('time') &&
            !iss.toLowerCase().includes('missing')
        );

        const newStatus =
          item.has_conflict ? 'conflict' : item.is_duplicate ? 'duplicate' : updatedIssues.length > 0 ? 'needs_review' : 'valid';

        return {
          ...item,
          title: editForm.title.trim() || item.title,
          day_of_week: fixedDay,
          day_name: DAY_LABELS[fixedDay] || 'Monday',
          start_time: fixedStartTime,
          end_time: fixedEndTime,
          location: editForm.location.trim() || null,
          course_code: editForm.course_code.trim() || null,
          status: newStatus,
          issues: updatedIssues,
        };
      })
    );
    setEditingId(null);
  };

  // ─── Step 7: Confirmation & Step 8: Persistence ────────────────────────────
  const proceedToConfirm = () => {
    const selectedCount = previewBlocks.filter((b, idx) =>
      checkedIds.has(b.temp_id || `item-${idx}`)
    ).length;
    if (selectedCount > 0) {
      setCurrentStep('confirm');
    }
  };

  const handleFinalConfirm = async () => {
    const selected = previewBlocks.filter((b, idx) => {
      const id = b.temp_id || `item-${idx}`;
      return checkedIds.has(id) && b.start_time && b.day_of_week >= 0;
    });

    if (selected.length === 0) return;

    setIsConfirming(true);

    try {
      const payload: IcsConfirmPayload = {
        preview_blocks: selected.map(b => ({
          title: b.title,
          day_of_week: b.day_of_week,
          start_time: b.start_time,
          end_time: b.end_time,
          location: b.location ?? null,
          effective_from: effectiveFrom || undefined,
          effective_until: effectiveUntil || undefined,
        })),
      };

      const res = await api.confirmFile(payload);
      await refreshWeek();

      const count = res.created_count ?? selected.length;
      const conflicts = res.conflicts_detected ?? 0;

      setImportSummary({ createdCount: count, conflictsDetected: conflicts });
      setCurrentStep('success');
      onToast('✓ Timetable imported');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to import timetable';
      setErrorDetails({
        title: 'Import Failed',
        message: msg,
      });
      setCurrentStep('error');
    } finally {
      setIsConfirming(false);
    }
  };

  if (!isOpen) return null;

  const checkedCount = previewBlocks.filter((b, idx) =>
    checkedIds.has(b.temp_id || `item-${idx}`)
  ).length;

  // Group preview items by day
  const groupedBlocks = DAY_ORDER.reduce<Record<number, FilePreviewItem[]>>((acc, day) => {
    const items = previewBlocks.filter(b => b.day_of_week === day);
    if (items.length > 0) acc[day] = items;
    return acc;
  }, {});

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-[var(--modal-overlay)] backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="w-full max-w-xl bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-2xl text-[var(--text-primary)] flex flex-col gap-4 max-h-[92vh] overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3 shrink-0">
          <div>
            <h2 id="import-modal-title" className="text-base font-semibold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
              <span className="text-indigo-500 font-bold">📅</span> Import Timetable
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Upload your university timetable and SyncShift will extract classes automatically
            </p>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition cursor-pointer text-sm"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          onChange={handleFileChange}
          className="hidden"
          id="timetable-file-input"
        />

        {/* ─── STEP 1: Upload Screen ─── */}
        {currentStep === 'upload' && (
          <div className="flex flex-col gap-4 py-2">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center
                ${isDragOver
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-[var(--border-color)] hover:border-indigo-500/60 bg-[var(--bg-elevated)] hover:bg-[var(--bg-secondary)]'
                }
              `}
            >
              <div className="w-12 h-12 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] flex items-center justify-center text-xl shadow-xs mb-3 text-indigo-500">
                📄
              </div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Drag &amp; drop your timetable file here
              </p>
              <p className="text-xs text-[var(--text-secondary)] mt-1">or</p>
              <button
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="mt-2.5 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium shadow-xs transition-colors cursor-pointer"
              >
                Choose file
              </button>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 text-[11px] text-[var(--text-muted)] font-mono">
                <span>PDF</span>
                <span>•</span>
                <span>DOCX</span>
                <span>•</span>
                <span>PPTX</span>
                <span>•</span>
                <span>JPG</span>
                <span>•</span>
                <span>PNG</span>
                <span>•</span>
                <span>TXT</span>
                <span>•</span>
                <span>ICS</span>
              </div>
            </div>

            {/* Client-side Validation Error if any */}
            {fileValidationError && (
              <div className="p-3 bg-[var(--conflict-bg)] border border-[var(--conflict-border)] rounded-xl text-xs text-[var(--conflict-text)] flex items-center gap-2">
                <span>⚠</span>
                <span>{fileValidationError}</span>
              </div>
            )}

            <div className="flex items-center justify-between text-xs text-[var(--text-muted)] px-1">
              <span>Maximum file size: 20MB</span>
              <span>All imports are private to your account</span>
            </div>
          </div>
        )}

        {/* ─── STEP 2: Processing Checklist ─── */}
        {currentStep === 'processing' && (
          <div className="py-8 px-4 flex flex-col items-center justify-center text-center gap-6">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-2xl animate-pulse">
              ⚡
            </div>

            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Analyzing timetable...
              </h3>
              <p className="text-xs text-[var(--text-muted)]">
                {selectedFile?.name ?? 'Extracting schedule information'}
              </p>
            </div>

            {/* Checklist items without fake percentages */}
            <div className="w-full max-w-xs bg-[var(--bg-elevated)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 text-left text-xs">
              {checklist.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <span className={`flex items-center gap-2 ${
                    item.status === 'completed'
                      ? 'text-[var(--text-primary)] font-medium'
                      : item.status === 'in_progress'
                      ? 'text-indigo-500 font-medium'
                      : 'text-[var(--text-muted)]'
                  }`}>
                    {item.status === 'completed' ? (
                      <span className="text-emerald-500 font-bold">✓</span>
                    ) : item.status === 'in_progress' ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping inline-block" />
                    ) : (
                      <span className="text-[var(--text-muted)]">○</span>
                    )}
                    {item.label}
                  </span>
                  <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                    {item.status === 'completed' ? 'Done' : item.status === 'in_progress' ? 'Running' : 'Waiting'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── STEP 5 & 6: Timetable Preview & Review ─── */}
        {currentStep === 'preview' && (
          <div className="flex flex-col gap-3 min-h-0 flex-1">
            {/* Step 4: Validation Summary Bar */}
            <div className="bg-[var(--bg-elevated)] border border-[var(--border-color)] rounded-xl p-3 text-xs flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[var(--text-primary)] font-medium">
                  Detected: <strong className="text-[var(--text-primary)]">{totalFound}</strong> events
                </span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                  <span>✓</span> {validCount} valid
                </span>
                {reviewCount > 0 && (
                  <span className="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1">
                    <span>⚠</span> {reviewCount} need review
                  </span>
                )}
                {duplicateCount > 0 && (
                  <span className="text-zinc-500 dark:text-zinc-400 font-medium flex items-center gap-1">
                    <span>⚠</span> {duplicateCount} possible duplicate{duplicateCount > 1 ? 's' : ''}
                  </span>
                )}
                {conflictCount > 0 && (
                  <span className="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1">
                    <span>🔴</span> {conflictCount} conflict{conflictCount > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <span className="text-[11px] text-[var(--text-muted)] font-mono">
                {checkedCount} of {previewBlocks.length} selected
              </span>
            </div>

            {/* Semester Effective Date Pickers */}
            <div className="p-2.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl flex flex-col sm:flex-row items-center gap-2 text-xs">
              <span className="text-[11px] font-medium text-[var(--text-secondary)] shrink-0">Schedule Dates:</span>
              <div className="flex items-center gap-2 w-full">
                <div className="flex-1">
                  <DatePicker value={effectiveFrom} onChange={setEffectiveFrom} />
                </div>
                <span className="text-[var(--text-muted)]">to</span>
                <div className="flex-1">
                  <DatePicker value={effectiveUntil} onChange={setEffectiveUntil} nullable minDate={effectiveFrom ?? undefined} />
                </div>
              </div>
            </div>

            {/* Select / Deselect and Instructions */}
            <div className="flex items-center justify-between px-1 text-xs text-[var(--text-muted)]">
              <span>Review extracted classes before confirming:</span>
              <button
                type="button"
                onClick={toggleAll}
                className="text-xs text-indigo-500 hover:text-indigo-400 font-medium cursor-pointer"
              >
                {checkedCount === previewBlocks.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>

            {/* Human-readable timetable preview grouped by day */}
            <div className="overflow-y-auto max-h-[300px] space-y-3 pr-1 text-xs">
              {Object.keys(groupedBlocks).length === 0 ? (
                <div className="p-6 text-center text-xs text-[var(--text-muted)]">
                  No classes detected.
                </div>
              ) : (
                Object.entries(groupedBlocks).map(([dayKey, blocks]) => {
                  const dayNum = parseInt(dayKey, 10);
                  const dayTitle = DAY_LABELS[dayNum] || 'Other';

                  return (
                    <div key={dayNum} className="space-y-1.5">
                      <div className="flex items-center gap-2 px-1">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                          {dayTitle}
                        </span>
                        <div className="h-px flex-1 bg-[var(--border-color)]" />
                      </div>

                      <div className="space-y-1.5">
                        {blocks.map((block, idx) => {
                          const id = block.temp_id || `item-${idx}`;
                          const isChecked = checkedIds.has(id);
                          const isEditing = editingId === id;

                          if (isEditing) {
                            return (
                              <div
                                key={id}
                                className="p-3 rounded-xl border border-indigo-500/50 bg-[var(--bg-elevated)] space-y-2.5 shadow-xs"
                              >
                                <div className="text-[11px] font-semibold text-indigo-500 flex items-center justify-between">
                                  <span>Edit Event</span>
                                  <button
                                    type="button"
                                    onClick={cancelEditing}
                                    className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                                  >
                                    Cancel
                                  </button>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  <div>
                                    <label className="text-[10px] text-[var(--text-muted)] block mb-0.5">Title</label>
                                    <input
                                      type="text"
                                      value={editForm.title}
                                      onChange={e => setEditForm(prev => ({ ...prev, title: e.target.value }))}
                                      className="w-full px-2.5 py-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-xs text-[var(--text-primary)]"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-[10px] text-[var(--text-muted)] block mb-0.5">Day</label>
                                    <CustomSelect
                                      options={[
                                        { value: '0', label: 'Monday' },
                                        { value: '1', label: 'Tuesday' },
                                        { value: '2', label: 'Wednesday' },
                                        { value: '3', label: 'Thursday' },
                                        { value: '4', label: 'Friday' },
                                        { value: '5', label: 'Saturday' },
                                        { value: '6', label: 'Sunday' },
                                      ]}
                                      value={String(editForm.day_of_week)}
                                      onChange={(val) => setEditForm((prev) => ({ ...prev, day_of_week: parseInt(val, 10) }))}
                                      size="sm"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-[10px] text-[var(--text-muted)] block mb-0.5">Start Time (HH:MM)</label>
                                    <input
                                      type="text"
                                      placeholder="09:00"
                                      value={editForm.start_time}
                                      onChange={e => setEditForm(prev => ({ ...prev, start_time: e.target.value }))}
                                      className="w-full px-2.5 py-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-xs text-[var(--text-primary)]"
                                    />
                                  </div>
                                  <div>
                                    <label className="text-[10px] text-[var(--text-muted)] block mb-0.5">End Time (HH:MM)</label>
                                    <input
                                      type="text"
                                      placeholder="10:30"
                                      value={editForm.end_time}
                                      onChange={e => setEditForm(prev => ({ ...prev, end_time: e.target.value }))}
                                      className="w-full px-2.5 py-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-xs text-[var(--text-primary)]"
                                    />
                                  </div>
                                </div>
                                <div className="flex justify-end gap-2 pt-1">
                                  <button
                                    type="button"
                                    onClick={cancelEditing}
                                    className="px-2.5 py-1 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] cursor-pointer"
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => saveEditing(id)}
                                    className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-[11px] text-white font-medium cursor-pointer"
                                  >
                                    Save changes
                                  </button>
                                </div>
                              </div>
                            );
                          }

                          return (
                            <div
                              key={id}
                              className={`
                                p-3 rounded-xl border flex items-start gap-3 transition-colors
                                ${isChecked
                                  ? block.has_conflict
                                    ? 'bg-[var(--conflict-bg)] border-[var(--conflict-border)]'
                                    : block.status === 'needs_review'
                                    ? 'bg-[var(--warning-bg)] border-[var(--warning-border)]'
                                    : 'bg-[var(--class-bg)] border-[var(--class-border)]'
                                  : 'bg-[var(--bg-card)] border-[var(--border-color)] opacity-70'
                                }
                              `}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => toggleChecked(id)}
                                className="mt-1 accent-indigo-600 rounded cursor-pointer w-4 h-4 shrink-0"
                                aria-label={`Select ${block.title}`}
                              />

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2 flex-wrap">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="font-semibold text-xs text-[var(--text-primary)]">
                                      {block.title}
                                    </span>
                                    {block.course_code && (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                                        {block.course_code}
                                      </span>
                                    )}
                                  </div>

                                  <div className="flex items-center gap-1.5 shrink-0">
                                    {/* Non-color only status badges */}
                                    {block.has_conflict ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30 flex items-center gap-1">
                                        <span>🔴</span> Conflict
                                      </span>
                                    ) : block.is_duplicate ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-500/15 text-zinc-700 dark:text-zinc-300 border border-zinc-500/30 flex items-center gap-1">
                                        <span>⚠</span> Duplicate
                                      </span>
                                    ) : block.status === 'needs_review' ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/15 text-amber-800 dark:text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                        <span>⚠</span> Needs review
                                      </span>
                                    ) : (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                        <span>✓</span> Valid
                                      </span>
                                    )}

                                    <button
                                      type="button"
                                      onClick={() => startEditing(block, id)}
                                      className="text-[11px] text-[var(--text-muted)] hover:text-indigo-500 ml-1 px-1.5 py-0.5 rounded hover:bg-[var(--bg-elevated)] cursor-pointer"
                                    >
                                      Edit
                                    </button>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] mt-1 flex-wrap font-mono">
                                  <span>{block.start_time || '??:??'} – {block.end_time || '??:??'}</span>
                                  {block.location && (
                                    <>
                                      <span className="text-[var(--text-muted)]">•</span>
                                      <span className="text-[var(--text-muted)] truncate flex items-center gap-1">
                                        <span>📍</span> {block.location}
                                      </span>
                                    </>
                                  )}
                                </div>

                                {/* Warning / conflict descriptions */}
                                {block.conflict_description && (
                                  <p className="text-[11px] text-rose-600 dark:text-rose-400 mt-1 flex items-center gap-1">
                                    <span>⚠</span> {block.conflict_description}
                                  </p>
                                )}
                                {block.duplicate_reason && !block.conflict_description && (
                                  <p className="text-[11px] text-[var(--text-muted)] mt-1 flex items-center gap-1">
                                    <span>ℹ</span> {block.duplicate_reason}
                                  </p>
                                )}
                                {block.issues && block.issues.length > 0 && !block.conflict_description && !block.duplicate_reason && (
                                  <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
                                    <span>⚠</span> {block.issues[0]}
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* ─── STEP 7: Explicit Confirmation View ─── */}
        {currentStep === 'confirm' && (
          <div className="py-6 px-3 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-xl text-indigo-500">
              📅
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                Import {checkedCount} event{checkedCount !== 1 ? 's' : ''}?
              </h3>
              <p className="text-xs text-[var(--text-secondary)] max-w-sm">
                This will add these verified classes to your calendar. Nothing is committed until you confirm.
              </p>
            </div>

            {/* Summary statistics */}
            <div className="w-full max-w-xs bg-[var(--bg-elevated)] border border-[var(--border-color)] rounded-xl p-3 text-xs space-y-1.5 text-left">
              <div className="flex justify-between text-[var(--text-secondary)]">
                <span>Classes to add:</span>
                <strong className="text-[var(--text-primary)]">{checkedCount}</strong>
              </div>
              {conflictCount > 0 && (
                <div className="flex justify-between text-rose-600 dark:text-rose-400">
                  <span>Schedule conflicts:</span>
                  <strong>{conflictCount}</strong>
                </div>
              )}
              {reviewCount > 0 && (
                <div className="flex justify-between text-amber-600 dark:text-amber-400">
                  <span>Warnings / flagged:</span>
                  <strong>{reviewCount}</strong>
                </div>
              )}
            </div>

            <div className="flex gap-2.5 w-full max-w-xs mt-2">
              <button
                type="button"
                onClick={() => setCurrentStep('preview')}
                className="flex-1 py-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] text-xs font-medium text-[var(--text-secondary)] cursor-pointer transition-colors"
              >
                Back to review
              </button>
              <button
                type="button"
                disabled={isConfirming}
                onClick={handleFinalConfirm}
                className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-xs cursor-pointer transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                {isConfirming ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Importing...</span>
                  </>
                ) : (
                  <span>Confirm import</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 8: Success State ─── */}
        {currentStep === 'success' && (
          <div className="py-8 px-4 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-2xl text-emerald-500">
              ✓
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                Timetable imported
              </h3>
              <p className="text-xs text-[var(--text-secondary)] max-w-xs">
                {importSummary.createdCount} classes added to your calendar.
                {importSummary.conflictsDetected > 0 && (
                  <span className="block text-rose-600 dark:text-rose-400 font-medium mt-1">
                    🔴 {importSummary.conflictsDetected} conflict{importSummary.conflictsDetected > 1 ? 's' : ''} detected with existing shifts.
                  </span>
                )}
              </p>
            </div>

            <div className="flex gap-2.5 mt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-xs cursor-pointer transition-colors"
              >
                View calendar
              </button>
            </div>
          </div>
        )}

        {/* ─── Error Recovery State ─── */}
        {currentStep === 'error' && (
          <div className="py-6 px-4 flex flex-col items-center justify-center text-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-xl text-rose-500">
              ⚠
            </div>
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              {errorDetails.title}
            </h3>
            <p className="text-xs text-[var(--text-secondary)] max-w-sm leading-relaxed">
              {errorDetails.message}
            </p>

            <div className="w-full max-w-xs p-3 bg-[var(--bg-elevated)] border border-[var(--border-color)] rounded-xl text-left text-xs space-y-1 text-[var(--text-secondary)] mt-1">
              <p className="font-medium text-[var(--text-primary)] text-[11px]">You can try:</p>
              <p>• Exporting timetable as PDF from student portal</p>
              <p>• Taking a higher contrast screenshot</p>
              <p>• Exporting an .ics file from your school calendar</p>
              <p>• Adding classes manually via calendar</p>
            </div>

            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => {
                  resetState();
                  fileInputRef.current?.click();
                }}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white rounded-xl cursor-pointer transition-colors"
              >
                Try another file
              </button>
              <button
                type="button"
                onClick={handleClose}
                className="px-3.5 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-xl cursor-pointer transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ─── Modal Footer Controls ─── */}
        {currentStep === 'preview' && (
          <div className="flex justify-between items-center pt-3 border-t border-[var(--border-color)] shrink-0">
            <button
              type="button"
              onClick={() => {
                resetState();
                fileInputRef.current?.click();
              }}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] underline cursor-pointer"
            >
              Choose another file
            </button>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-3.5 py-1.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] text-xs font-medium text-[var(--text-secondary)] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={checkedCount === 0}
                onClick={proceedToConfirm}
                className="px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
              >
                Import {checkedCount} event{checkedCount !== 1 ? 's' : ''}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
