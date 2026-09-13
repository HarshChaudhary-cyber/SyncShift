'use client';

import React, { useState } from 'react';
import { PlanOption, SmartPlanPreviewResponse } from '@/lib/api';

interface PlanOptionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  previewData: SmartPlanPreviewResponse | null;
  onApplyPlan: (option: PlanOption) => Promise<void>;
  isApplying: boolean;
}

export default function PlanOptionsModal({
  isOpen,
  onClose,
  previewData,
  onApplyPlan,
  isApplying,
}: PlanOptionsModalProps) {
  const [selectedOptionId, setSelectedOptionId] = useState<string>('balanced');
  const [showDetails, setShowDetails] = useState(false);

  if (!isOpen || !previewData) return null;

  const selectedOption =
    previewData.options.find((o) => o.id === selectedOptionId) ||
    previewData.options[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between bg-gradient-to-r from-purple-950/30 via-transparent to-transparent">
          <div className="space-y-0.5">
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-purple-400 uppercase tracking-wider">
              <span>🗓️</span>
              <span>Week of {previewData.week_start} to {previewData.week_end}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)]">
              Choose your schedule strategy
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              SyncShift generated {previewData.options.length} feasible, conflict-free options based on your classes and commitments.
            </p>
          </div>

          <button
            onClick={onClose}
            disabled={isApplying}
            className="w-9 h-9 rounded-full bg-[var(--bg-secondary)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-center transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Strategy Tabs */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {previewData.options.map((opt) => {
              const isSelected = opt.id === selectedOption?.id;
              const isRecommended = opt.id === 'balanced';

              return (
                <div
                  key={opt.id}
                  onClick={() => setSelectedOptionId(opt.id)}
                  className={`relative p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between text-left ${
                    isSelected
                      ? 'bg-purple-950/20 border-purple-500/80 shadow-lg shadow-purple-950/30 ring-1 ring-purple-500/50'
                      : 'bg-[var(--bg-secondary)] border-[var(--border-color)] hover:border-purple-500/40 opacity-80 hover:opacity-100'
                  }`}
                >
                  {isRecommended && (
                    <span className="absolute -top-2.5 right-4 px-2.5 py-0.5 rounded-full bg-purple-600 text-[10px] font-bold text-white shadow-sm">
                      Recommended
                    </span>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-base text-[var(--text-primary)]">
                        {opt.name}
                      </h3>
                      <div className="px-2.5 py-1 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-300 font-extrabold text-xs">
                        {opt.score}/100
                      </div>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed line-clamp-2">
                      {opt.description}
                    </p>
                  </div>

                  <div className="pt-4 mt-3 border-t border-[var(--border-color)]/60 flex items-center justify-between text-xs text-[var(--text-secondary)]">
                    <span>{opt.summary.added_study_blocks_count} study blocks</span>
                    <span className="text-purple-400 font-semibold">{opt.summary.total_study_hours}h total</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Option Details */}
          {selectedOption && (
            <div className="rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border-color)] p-5 space-y-5">
              {/* Change Impact Preview Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-3 rounded-xl bg-purple-950/30 border border-purple-800/40">
                  <div className="text-lg font-bold text-purple-300">
                    +{selectedOption.summary.added_study_blocks_count}
                  </div>
                  <div className="text-[11px] text-purple-400/80 uppercase tracking-wide font-medium">
                    Study Blocks Added
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-blue-950/30 border border-blue-800/40">
                  <div className="text-lg font-bold text-blue-300">
                    {selectedOption.summary.unchanged_classes_count}
                  </div>
                  <div className="text-[11px] text-blue-400/80 uppercase tracking-wide font-medium">
                    Classes Unchanged (Fixed)
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/40">
                  <div className="text-lg font-bold text-amber-300">
                    {selectedOption.summary.unchanged_fixed_commitments_count}
                  </div>
                  <div className="text-[11px] text-amber-400/80 uppercase tracking-wide font-medium">
                    Fixed Shifts Intact
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-800/40">
                  <div className="text-lg font-bold text-emerald-300">
                    0
                  </div>
                  <div className="text-[11px] text-emerald-400/80 uppercase tracking-wide font-medium">
                    Conflicts Detected
                  </div>
                </div>
              </div>

              {/* Reasons & Explanations */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                  Why this plan works:
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {selectedOption.reasons.map((reason, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 text-xs text-[var(--text-primary)] font-medium"
                    >
                      <span>{reason}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Trade-off summary */}
              {selectedOption.trade_offs && (
                <div className="p-3.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-secondary)]">
                  <strong className="text-[var(--text-primary)]">Strategy Trade-off: </strong>
                  {selectedOption.trade_offs}
                </div>
              )}

              {/* Toggle Proposed Time Slots List */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                    Proposed Study Schedule ({selectedOption.added_blocks.length} sessions)
                  </h4>
                  <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="text-xs text-purple-400 hover:text-purple-300 font-semibold underline cursor-pointer"
                  >
                    {showDetails ? 'Hide Session List' : 'View Session List'}
                  </button>
                </div>

                {showDetails && (
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                    {selectedOption.added_blocks.map((blk) => (
                      <div
                        key={blk.temp_id}
                        className="flex items-center justify-between p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs"
                      >
                        <div className="flex items-center gap-3">
                          <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shrink-0" />
                          <div>
                            <div className="font-bold text-[var(--text-primary)]">{blk.title}</div>
                            <div className="text-[var(--text-secondary)] text-[11px]">
                              {blk.day_name}, {blk.date}
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="font-semibold text-purple-300">
                            {blk.start_time.slice(0, 5)} – {blk.end_time.slice(0, 5)}
                          </div>
                          <div className="text-[var(--text-secondary)] text-[11px]">
                            {blk.duration_hours}h focus
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-[var(--border-color)] flex items-center justify-end gap-3 bg-[var(--bg-secondary)]">
          <button
            onClick={onClose}
            disabled={isApplying}
            className="px-4 py-2.5 rounded-xl border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--border-color)] font-semibold transition cursor-pointer"
          >
            Cancel
          </button>

          {selectedOption && (
            <button
              onClick={() => onApplyPlan(selectedOption)}
              disabled={isApplying || !selectedOption.summary.is_valid}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer"
            >
              {isApplying ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Applying to Calendar...</span>
                </>
              ) : (
                <>
                  <span>✓</span>
                  <span>Apply "{selectedOption.name}"</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
