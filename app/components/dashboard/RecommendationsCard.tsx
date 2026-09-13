'use client';

import React from 'react';

interface RecommendationsCardProps {
  recommendations?: string[];
  loading?: boolean;
}

export default function RecommendationsCard({
  recommendations = [],
  loading,
}: RecommendationsCardProps) {
  if (loading) {
    return (
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl animate-pulse space-y-3">
        <div className="h-5 bg-[var(--bg-secondary)] rounded w-1/4" />
        <div className="space-y-2">
          <div className="h-10 bg-[var(--bg-secondary)] rounded-xl" />
          <div className="h-10 bg-[var(--bg-secondary)] rounded-xl" />
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) return null;

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 sm:p-6 shadow-xl space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-base">💡</span>
        <h3 className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase">
          Recommendations
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {recommendations.map((rec, idx) => {
          const isWarning = rec.startsWith('⚠');
          const isBook = rec.startsWith('📚');
          const isBriefcase = rec.startsWith('💼');
          const isCheck = rec.startsWith('✓');

          const icon = isWarning ? '⚠' : isBook ? '📚' : isBriefcase ? '💼' : isCheck ? '✓' : '•';
          const cleanText = rec.replace(/^[⚠📚💼✓•]\s*/, '');

          return (
            <div
              key={idx}
              className={`p-3 rounded-xl border flex items-start gap-2.5 transition ${
                isWarning
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200'
                  : isBook
                  ? 'bg-purple-500/10 border-purple-500/30 text-purple-900 dark:text-purple-200'
                  : isBriefcase
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-900 dark:text-blue-200'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200'
              }`}
            >
              <span className="shrink-0 text-sm mt-0.5">{icon}</span>
              <p className="text-xs font-semibold leading-relaxed">{cleanText}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
