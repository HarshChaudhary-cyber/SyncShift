'use client';

import React from 'react';
import {
  SparklesIcon,
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  BookOpenIcon,
  BriefcaseIcon,
  BuildingLibraryIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';

interface SuggestedPrompt {
  title: string;
  prompt: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
}

export default function StudentAssistantPage() {
  const suggestedPrompts: SuggestedPrompt[] = [
    {
      title: 'Check Schedule Conflicts',
      prompt: 'Do I have any schedule conflicts between my university lectures and work shifts this week?',
      icon: ExclamationTriangleIcon,
    },
    {
      title: 'Find Study Time Gaps',
      prompt: 'Look at my schedule for the upcoming week and suggest the best open gaps for 2-hour study sessions.',
      icon: BookOpenIcon,
    },
    {
      title: 'Weekly Work Hours',
      prompt: 'How many total hours am I scheduled to work this week, and how close am I to my weekly limit?',
      icon: BriefcaseIcon,
    },
    {
      title: 'Next Class Preparation',
      prompt: 'What is my next upcoming university lecture, what room is it in, and what time does it start?',
      icon: BuildingLibraryIcon,
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Hero */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-6 sm:p-8 shadow-sm text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-xs">
          <SparklesIcon className="w-7 h-7" aria-hidden="true" />
        </div>
        <div className="space-y-1.5 max-w-lg mx-auto">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
            SyncShift Assistant
          </h1>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
            Your university and personal schedule intelligence. SyncShift analyzes timetables,
            detects conflicts, and helps optimize your daily routine.
          </p>
        </div>
        <div className="pt-2">
          <button
            type="button"
            onClick={() => openSyncShiftAssistant()}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-sm transition transform hover:-translate-y-0.5 cursor-pointer inline-flex items-center gap-2"
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4" aria-hidden="true" />
            <span>Launch SyncShift Assistant</span>
          </button>
        </div>
      </div>

      {/* Suggested Prompts */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Quick Inquiries</h2>
          <span className="text-xs text-[var(--text-muted)]">Click any prompt to review in the assistant</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {suggestedPrompts.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                role="button"
                tabIndex={0}
                onClick={() => openSyncShiftAssistant(item.prompt)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openSyncShiftAssistant(item.prompt);
                  }
                }}
                className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/50 hover:bg-[var(--bg-secondary)] transition cursor-pointer space-y-2 group shadow-2xs text-left focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
                    <Icon className="w-4 h-4" aria-hidden="true" />
                    <h3 className="text-xs font-bold text-[var(--text-primary)] group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition">
                      {item.title}
                    </h3>
                  </div>
                  <ArrowRightIcon className="w-3.5 h-3.5 text-[var(--text-muted)] group-hover:text-indigo-500 group-hover:translate-x-0.5 transition" aria-hidden="true" />
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  &ldquo;{item.prompt}&rdquo;
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Privacy Notice */}
      <div className="p-4 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl flex items-start gap-3 text-xs text-[var(--text-secondary)] shadow-2xs">
        <ShieldCheckIcon className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="leading-relaxed">
          <span className="font-semibold text-[var(--text-primary)]">Privacy & Scope Guarantee: </span>
          SyncShift Assistant operates exclusively on your authorized calendar events and academic timetable permissions. Private work shifts and personal commitments are never disclosed to course instructors or administrators.
        </div>
      </div>
    </div>
  );
}
