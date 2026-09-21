'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CalendarDaysIcon, ExclamationTriangleIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const PAIN_POINTS = [
  {
    icon: CalendarDaysIcon,
    emoji: '📅',
    title: 'Your timetable changes. Your job doesn’t.',
    desc: 'Universities shift seminar slots and lecture halls with zero regard for your employer’s fixed weekly shifts and manager’s rota.',
    accent: 'from-blue-500/20 to-blue-500/5',
    border: 'group-hover:border-blue-500/50',
    iconColor: 'text-blue-600 dark:text-blue-400',
    badge: 'Shift Lock-In',
  },
  {
    icon: ExclamationTriangleIcon,
    emoji: '⚠️',
    title: 'You only find conflicts after you’ve registered.',
    desc: 'By the time course registration closes, you realize mandatory lab sessions collide directly with your highest-paying café shift.',
    accent: 'from-amber-500/20 to-amber-500/5',
    border: 'group-hover:border-amber-500/50',
    iconColor: 'text-amber-600 dark:text-amber-400',
    badge: 'Double Booking',
  },
  {
    icon: ChartBarIcon,
    emoji: '📊',
    title: 'No one tells you when you’re overcommitting.',
    desc: 'Tracking the strict 20h/week student work limit across odd shifts and exams shouldn’t require mental math or messy spreadsheets.',
    accent: 'from-rose-500/20 to-rose-500/5',
    border: 'group-hover:border-rose-500/50',
    iconColor: 'text-rose-600 dark:text-rose-400',
    badge: 'Visa Risk',
  },
];

export default function ProblemSection() {
  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-secondary)] border-t border-[var(--border-color)] overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-indigo-950/20 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-50 dark:bg-red-950/40 border border-rose-200 dark:border-red-800/40 text-xs font-semibold text-rose-700 dark:text-red-300 mb-4"
          >
            <span>The Student Worker Dilemma</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl md:text-5xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
          >
            University scheduling{' '}
            <span className="bg-gradient-to-r from-red-400 via-rose-300 to-amber-300 bg-clip-text text-transparent">
              ignores your real life
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-4 text-sm sm:text-base text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            Universities design timetables assuming studying is your only commitment. When you work to support yourself, small overlaps turn into academic catastrophes.
          </motion.p>
        </div>

        {/* 3 Pain Points Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {PAIN_POINTS.map((card, idx) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 35 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.6, delay: idx * 0.15 }}
                className={`group relative rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-7 sm:p-8 flex flex-col justify-between hover:bg-[var(--bg-secondary)] transition-all duration-300 hover:shadow-2xl ${card.border}`}
              >
                {/* Subtle gradient splash inside card */}
                <div
                  className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${card.accent} opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none`}
                />

                <div className="relative z-10 space-y-5">
                  <div className="flex items-center justify-between">
                    <div className={`w-12 h-12 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-center text-xl shadow-inner ${card.iconColor}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                      {card.badge}
                    </span>
                  </div>

                  <h3 className="text-lg sm:text-xl font-bold text-[var(--text-primary)] tracking-tight leading-snug">
                    {card.title}
                  </h3>

                  <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
                    {card.desc}
                  </p>
                </div>

                <div className="relative z-10 mt-6 pt-5 border-t border-[var(--border-color)] flex items-center justify-between text-xs text-[var(--text-muted)] group-hover:text-[var(--text-secondary)] transition-colors">
                  <span>Pain Point #{idx + 1}</span>
                  <span className="text-[var(--text-muted)] font-mono">0{idx + 1}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
