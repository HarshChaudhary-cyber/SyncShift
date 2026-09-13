'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  CalendarDaysIcon,
  ExclamationTriangleIcon,
  ArrowUpTrayIcon,
  BellAlertIcon,
  BriefcaseIcon,
  DevicePhoneMobileIcon,
} from '@heroicons/react/24/outline';

const FEATURES = [
  {
    icon: CalendarDaysIcon,
    emoji: '🗓️',
    title: 'Week View Calendar',
    highlight: 'Drag and drop to reschedule',
    desc: 'Interactive 7-day grid built for students. Drag shift blocks to explore what-if moves, snap times in 15-minute intervals, and visualize open study slots.',
    color: 'from-indigo-500/20 to-indigo-500/5',
    iconColor: 'text-indigo-400',
    border: 'group-hover:border-indigo-500/50',
    badge: 'Interactive UX',
  },
  {
    icon: ExclamationTriangleIcon,
    emoji: '⚠️',
    title: 'Real-time Conflicts',
    highlight: 'Instant red alerts when schedules clash',
    desc: 'Sweep-line algorithm detects overlapping minutes between lectures, lab sessions, and job shifts instantly. See exact clash durations and involved courses.',
    color: 'from-rose-500/20 to-rose-500/5',
    iconColor: 'text-rose-400',
    border: 'group-hover:border-rose-500/50',
    badge: 'Zero Clashes',
  },
  {
    icon: ArrowUpTrayIcon,
    emoji: '📤',
    title: 'Smart Import',
    highlight: 'Upload PDF, image, or .ics from any university',
    desc: 'Direct parser support for .ics calendars, HISinOne, C@MPUS, plus OCR screenshot parsing to turn any PDF syllabus or photo timetable into clean calendar events.',
    color: 'from-blue-500/20 to-blue-500/5',
    iconColor: 'text-blue-400',
    border: 'group-hover:border-blue-500/50',
    badge: 'Universal Parser',
  },
  {
    icon: BellAlertIcon,
    emoji: '🔔',
    title: 'Reminders & Notifications',
    highlight: 'Never miss a class or shift start',
    desc: 'Timely in-app alerts and customizable email notifications before your earliest shifts and mandatory seminars so you always show up on time.',
    color: 'from-amber-500/20 to-amber-500/5',
    iconColor: 'text-amber-400',
    border: 'group-hover:border-amber-500/50',
    badge: 'Alert System',
  },
  {
    icon: BriefcaseIcon,
    emoji: '💼',
    title: 'Visa Compliance & Hours',
    highlight: 'Track your weekly work hours automatically',
    desc: 'Stay strictly under your 20h/week international student limit. Smart split logic handles overnight shifts crossing Sunday midnight seamlessly.',
    color: 'from-emerald-500/20 to-emerald-500/5',
    iconColor: 'text-emerald-400',
    border: 'group-hover:border-emerald-500/50',
    badge: 'Legal Safety',
  },
  {
    icon: DevicePhoneMobileIcon,
    emoji: '📱',
    title: 'Works Everywhere',
    highlight: 'Desktop and mobile, no app install needed',
    desc: 'Built as a lightning-fast responsive progressive web experience. Check your schedule on your phone between classes or on your laptop in the library.',
    color: 'from-purple-500/20 to-purple-500/5',
    iconColor: 'text-purple-400',
    border: 'group-hover:border-purple-500/50',
    badge: 'Mobile Optimized',
  },
];

export default function FeaturesSection() {
  return (
    <section
      id="features"
      className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-primary)] border-t border-[var(--border-color)] overflow-hidden"
    >
      {/* Background glow effects */}
      <div className="absolute top-1/4 right-10 w-[500px] h-[350px] bg-indigo-600/10 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-10 w-[450px] h-[300px] bg-rose-600/10 rounded-full blur-[150px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] mb-4 shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            <span>Engineered for Student Workers</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl md:text-5xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
          >
            Everything you need,{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-rose-300 to-amber-300 bg-clip-text text-transparent">
              nothing you don’t
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-4 text-sm sm:text-base text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            Built specifically around the intersection of academic schedules and hourly employment.
          </motion.p>
        </div>

        {/* 2x3 Grid on Desktop / 1 col on Mobile */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {FEATURES.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className={`group relative rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-7 flex flex-col justify-between hover:bg-[var(--bg-secondary)] transition-all duration-300 hover:shadow-2xl ${feature.border}`}
              >
                {/* Gradient background on hover */}
                <div
                  className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none`}
                />

                <div className="relative z-10 space-y-4">
                  <div className="flex items-center justify-between">
                    <div
                      className={`w-12 h-12 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] flex items-center justify-center shadow-inner ${feature.iconColor}`}
                    >
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                      {feature.badge}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
                      {feature.title}
                    </h3>
                    <p className="text-xs font-semibold text-indigo-400/90 mt-0.5">
                      {feature.highlight}
                    </p>
                  </div>

                  <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
                    {feature.desc}
                  </p>
                </div>

                <div className="relative z-10 mt-6 pt-4 border-t border-[var(--border-color)] flex items-center justify-between text-xs text-[var(--text-muted)]">
                  <span className="text-[var(--text-secondary)] font-mono text-[11px]">SyncShift Core</span>
                  <span className="text-[var(--text-muted)]">0{idx + 1}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
