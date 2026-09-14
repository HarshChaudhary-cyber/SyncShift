'use client';

import React, { useState, useEffect } from 'react';
import {
  api,
  TimetableVersionOut,
  VersionChecklistOut,
  PublishVersionResponse,
  UniversityNotificationSummaryOut,
  getErrorMessage,
} from '@/lib/api';

interface TimetablePublishModalProps {
  isOpen: boolean;
  onClose: () => void;
  institutionId: number;
  timetableId: number;
  timetableName: string;
  onPublished?: (summary?: PublishVersionResponse) => void;
}

export default function TimetablePublishModal({
  isOpen,
  onClose,
  institutionId,
  timetableId,
  timetableName,
  onPublished,
}: TimetablePublishModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Flow states: 'check' | 'publishing' | 'result' | 'delivery_report'
  const [step, setStep] = useState<'check' | 'publishing' | 'result' | 'delivery_report'>('check');
  const [targetVersion, setTargetVersion] = useState<TimetableVersionOut | null>(null);
  const [checklist, setChecklist] = useState<VersionChecklistOut | null>(null);
  const [publishResult, setPublishResult] = useState<PublishVersionResponse | null>(null);
  const [deliveryReport, setDeliveryReport] = useState<UniversityNotificationSummaryOut | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setStep('check');
      setError(null);
      setPublishResult(null);
      setDeliveryReport(null);
      return;
    }

    async function loadVersionState() {
      try {
        setLoading(true);
        setError(null);
        // 1. Fetch versions
        const versions = await api.getTimetableVersions(institutionId, timetableId);
        if (!versions || versions.length === 0) {
          setError('No timetable version found to publish.');
          setLoading(false);
          return;
        }

        // Find version to publish: prefer latest draft, in_review, or approved, or current published
        let ver = versions.find((v) => ['approved', 'in_review', 'draft'].includes(v.status));
        if (!ver) {
          ver = versions[0];
        }
        setTargetVersion(ver);

        // 2. Fetch checklist
        const chk = await api.getTimetableVersionChecklist(institutionId, timetableId, ver.id);
        setChecklist(chk);
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to prepare timetable for publishing.'));
      } finally {
        setLoading(false);
      }
    }

    loadVersionState();
  }, [isOpen, institutionId, timetableId]);

  const handlePublish = async () => {
    if (!targetVersion) return;
    try {
      setLoading(true);
      setError(null);
      setStep('publishing');

      // If version is draft or in_review, transition it to approved first if needed
      const verId = targetVersion.id;
      if (targetVersion.status === 'draft') {
        await api.submitVersionReview(institutionId, timetableId, verId, 'Auto-submitted for publishing');
        await api.approveTimetableVersion(institutionId, timetableId, verId, 'Approved for publishing');
      } else if (targetVersion.status === 'in_review') {
        await api.approveTimetableVersion(institutionId, timetableId, verId, 'Approved for publishing');
      }

      // Publish version atomically
      const res = await api.publishTimetableVersion(institutionId, timetableId, verId, {
        notes: 'Published official baseline timetable',
      });

      setPublishResult(res);
      setStep('result');
      if (onPublished) {
        onPublished(res);
      }
    } catch (err: any) {
      setError(getErrorMessage(err, 'Failed to publish timetable version.'));
      setStep('check');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDeliveryReport = async () => {
    if (!publishResult?.published_version?.id) return;
    try {
      setLoadingReport(true);
      setStep('delivery_report');
      const report = await api.getPublishNotificationSummary(
        institutionId,
        timetableId,
        publishResult.published_version.id
      );
      setDeliveryReport(report);
    } catch (err: any) {
      setError(getErrorMessage(err, 'Failed to load delivery report.'));
    } finally {
      setLoadingReport(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between bg-[var(--bg-secondary)]">
          <div>
            <h3 className="text-base font-bold text-[var(--text-primary)]">
              {step === 'result'
                ? 'Timetable Published 🎉'
                : step === 'delivery_report'
                ? 'Student Notification Delivery Report'
                : 'Publish University Timetable'}
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              {timetableName} • Version {targetVersion?.version_number || 1}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-medium">
              ⚠️ {error}
            </div>
          )}

          {/* STEP 1: Pre-publish validation checklist */}
          {step === 'check' && (
            <div className="space-y-4">
              {loading ? (
                <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                  Validating timetable conflicts and capacity...
                </div>
              ) : checklist ? (
                <div className="space-y-4">
                  {/* Status Card */}
                  <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--text-secondary)]">Readiness Status</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          checklist.is_publishable
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {checklist.is_publishable ? '✓ Ready to Publish' : '⚠️ Action Required'}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-primary)] font-medium">
                      {checklist.summary_message}
                    </p>
                    <div className="text-[11px] text-[var(--text-muted)] pt-1 flex gap-4">
                      <span>Scheduled Meetings: {checklist.total_meetings}</span>
                      <span>Sections Covered: {checklist.total_sections_scheduled}</span>
                    </div>
                  </div>

                  {/* Blocking issues list if any */}
                  {checklist.blocking_issues && checklist.blocking_issues.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-1.5">
                      <p className="text-xs font-bold text-rose-400">Blocking Issues (Must be resolved first):</p>
                      <ul className="text-xs text-rose-300 space-y-1 list-disc list-inside">
                        {checklist.blocking_issues.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Warning items if any */}
                  {checklist.warnings && checklist.warnings.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-1.5">
                      <p className="text-xs font-bold text-amber-400">Warnings (Non-blocking):</p>
                      <ul className="text-xs text-amber-300 space-y-1 list-disc list-inside">
                        {checklist.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-xs text-[var(--text-secondary)] leading-relaxed space-y-1">
                    <p className="font-bold text-indigo-400">What happens when you publish?</p>
                    <p>
                      1. Version {targetVersion?.version_number} becomes the official institutional timetable.
                    </p>
                    <p>
                      2. SyncShift automatically identifies all students enrolled in changed classes.
                    </p>
                    <p>
                      3. Targeted notifications (in-app, push, email) are sent automatically with exact before/after details.
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* STEP 2: Publishing in progress */}
          {step === 'publishing' && (
            <div className="p-12 text-center space-y-3">
              <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <h4 className="text-sm font-bold text-[var(--text-primary)]">Publishing Timetable Version...</h4>
              <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto">
                Committing official version, calculating enrolled student impacts, and generating targeted notifications.
              </p>
            </div>
          )}

          {/* STEP 3: Publication Result Screen */}
          {step === 'result' && publishResult && (
            <div className="space-y-4 animate-fade-in">
              {/* Success Banner */}
              <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-2">
                <span className="text-3xl block">🎉</span>
                <h4 className="text-base font-black text-emerald-400">TIMETABLE PUBLISHED</h4>
                <p className="text-xs text-emerald-300 font-medium">
                  Version {publishResult.published_version.version_number} is now official and active.
                </p>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center">
                  <div className="text-xl font-black text-indigo-400">
                    {publishResult.notification_summary?.students_affected ?? 0}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mt-1">
                    Students Affected
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center">
                  <div className="text-xl font-black text-amber-400">
                    {publishResult.notification_summary?.classes_changed ?? 0}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mt-1">
                    Class Changes
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] text-center">
                  <div className="text-xl font-black text-rose-400">
                    {publishResult.notification_summary?.new_conflicts ?? 0}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mt-1">
                    New Conflicts
                  </div>
                </div>
              </div>

              {/* Channels Status Card */}
              <div className="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-2.5">
                <span className="text-xs font-bold text-[var(--text-primary)] block">
                  Notification Delivery Channels:
                </span>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <div>
                      <span className="font-semibold block text-[11px]">In-app</span>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {publishResult.notification_summary?.in_app_delivered ?? 0} created
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <div>
                      <span className="font-semibold block text-[11px]">Email</span>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {publishResult.notification_summary?.email_delivered ?? 0} delivered
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <div>
                      <span className="font-semibold block text-[11px]">Push</span>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {publishResult.notification_summary?.push_delivered ?? 0} sent
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Student Delivery Report */}
          {step === 'delivery_report' && (
            <div className="space-y-3">
              <button
                onClick={() => setStep('result')}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 cursor-pointer"
              >
                <span>← Back to summary</span>
              </button>

              {loadingReport ? (
                <div className="p-8 text-center text-xs text-[var(--text-muted)]">Loading delivery report...</div>
              ) : deliveryReport ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                    <span>Total Dispatches: {deliveryReport.total_notifications}</span>
                    <span>Status: {deliveryReport.summary_status}</span>
                  </div>

                  <div className="max-h-60 overflow-y-auto border border-[var(--border-color)] rounded-xl divide-y divide-[var(--border-color)] text-xs">
                    {deliveryReport.logs.length === 0 ? (
                      <div className="p-4 text-center text-[var(--text-muted)]">No student dispatches recorded.</div>
                    ) : (
                      deliveryReport.logs.map((item) => (
                        <div key={item.id} className="p-2.5 flex items-center justify-between gap-2 hover:bg-[var(--bg-secondary)] transition">
                          <div>
                            <span className="font-bold text-[var(--text-primary)]">{item.student_name}</span>
                            <span className="text-[var(--text-muted)] ml-2 text-[11px]">[{item.type}]</span>
                            <p className="text-[11px] text-[var(--text-secondary)] line-clamp-1">{item.title}</p>
                          </div>
                          <div className="text-right shrink-0">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono font-bold ${
                              item.priority === 'URGENT' ? 'bg-rose-500/20 text-rose-400' : 'bg-indigo-500/20 text-indigo-400'
                            }`}>
                              {item.priority}
                            </span>
                            <span className="text-[10px] text-emerald-400 block mt-0.5">
                              {item.delivery_status} ({item.channel})
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] flex items-center justify-between">
          {step === 'check' && (
            <>
              <button
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 rounded-xl border border-[var(--border-color)] hover:bg-[var(--bg-card)] text-xs font-medium text-[var(--text-secondary)] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                disabled={loading || !checklist?.is_publishable}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold shadow-sm transition cursor-pointer flex items-center gap-1.5"
              >
                <span>🚀 Publish Timetable Now</span>
              </button>
            </>
          )}

          {step === 'result' && (
            <>
              <button
                onClick={handleOpenDeliveryReport}
                className="px-4 py-2 rounded-xl border border-[var(--border-color)] hover:bg-[var(--bg-card)] text-xs font-medium text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
              >
                View Delivery Report 📋
              </button>
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-sm transition cursor-pointer"
              >
                Done
              </button>
            </>
          )}

          {step === 'delivery_report' && (
            <div className="w-full flex justify-end">
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-sm transition cursor-pointer"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
