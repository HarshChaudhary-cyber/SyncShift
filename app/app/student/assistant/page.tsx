'use client';

import React from 'react';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';

export default function StudentAssistantPage() {
  const suggestedPrompts = [
    {
      title: 'Check Schedule Conflicts',
      prompt: 'Do I have any schedule conflicts between my university lectures and work shifts this week?',
      icon: '🚨',
    },
    {
      title: 'Find Study Time Gaps',
      prompt: 'Look at my schedule for the upcoming week and suggest the best open gaps for 2-hour study sessions.',
      icon: '📖',
    },
    {
      title: 'Weekly Work Hours',
      prompt: 'How many total hours am I scheduled to work this week, and how close am I to my weekly limit?',
      icon: '💼',
    },
    {
      title: 'Next Class Preparation',
      prompt: 'What is my next upcoming university lecture, what room is it in, and what time does it start?',
      icon: '🏛️',
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Hero */}
      <div className="bg-gradient-to-br from-indigo-900/40 via-purple-900/30 to-slate-900/40 border border-indigo-500/30 rounded-3xl p-8 shadow-xl text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-3xl shadow-lg">
          ✨
        </div>
        <h1 className="text-2xl font-black text-[var(--text-primary)] tracking-tight">
          Ask SyncShift AI Assistant
        </h1>
        <p className="text-sm text-[var(--text-secondary)] max-w-lg mx-auto">
          Your personal academic and work schedule intelligence. SyncShift AI analyzes your timetables,
          detects conflicts, and helps optimize your daily student routine.
        </p>
        <div className="pt-2">
          <button
            onClick={() => openSyncShiftAssistant()}
            className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-2xl text-sm font-bold shadow-xl shadow-indigo-950/50 transition transform hover:-translate-y-0.5 cursor-pointer inline-flex items-center gap-2"
          >
            <span>💬 Launch SyncShift AI Chat</span>
          </button>
        </div>
      </div>

      {/* Suggested Prompts */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Quick Inquiries</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {suggestedPrompts.map((item, idx) => (
            <div
              key={idx}
              onClick={() => openSyncShiftAssistant()}
              className="p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/50 hover:bg-[var(--bg-secondary)] transition cursor-pointer space-y-2 group shadow-sm"
            >
              <div className="flex items-center gap-2.5">
                <span className="text-xl">{item.icon}</span>
                <h3 className="text-sm font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition">
                  {item.title}
                </h3>
              </div>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                &ldquo;{item.prompt}&rdquo;
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Privacy Notice */}
      <div className="p-4 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl flex items-start gap-3 text-xs text-[var(--text-secondary)]">
        <span className="text-base">🛡️</span>
        <div>
          <span className="font-bold text-[var(--text-primary)]">Privacy & Scope Guarantee: </span>
          SyncShift AI only analyzes your personal authorized calendar data. Your private job shifts and personal tasks are never shared with university faculty.
        </div>
      </div>
    </div>
  );
}
