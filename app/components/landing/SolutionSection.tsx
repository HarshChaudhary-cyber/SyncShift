'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  ArrowUpTrayIcon,
  CalendarIcon,
  ExclamationCircleIcon,
  CheckBadgeIcon,
} from '@heroicons/react/24/outline';

const STEPS = [
  {
    number: '01',
    title: 'Upload your timetable',
    subtitle: 'Drop file or import .ics',
    desc: 'Export from your university portal (HISinOne, C@MPUS, Moodle, or raw .ics file). SyncShift automatically extracts course names, rooms, and recurring slots.',
    icon: ArrowUpTrayIcon,
    tag: 'Universities Supported',
    accentColor: 'text-indigo-400',
    borderColor: 'border-indigo-500/30',
    bgColor: 'bg-indigo-500/10',
  },
  {
    number: '02',
    title: 'Add your work shifts',
    subtitle: 'Recurring or weekly rotas',
    desc: 'Input your café, tutoring, or campus job hours. Set hourly pay to track earnings and lock in recurring weekly commitments in seconds.',
    icon: CalendarIcon,
    tag: 'Fast & Flexible',
    accentColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    bgColor: 'bg-emerald-500/10',
  },
  {
    number: '03',
    title: 'See conflicts instantly',
    subtitle: 'Real-time clash detection',
    desc: 'SyncShift computes overlapping minutes instantly. Receive red warnings on your calendar and swap seminar sections before the semester starts.',
    icon: ExclamationCircleIcon,
    tag: 'Zero Double-Bookings',
    accentColor: 'text-rose-400',
    borderColor: 'border-rose-500/30',
    bgColor: 'bg-rose-500/10',
  },
];

export default function SolutionSection() {
  return (
    <section
      id="how-it-works"
      className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-primary)] border-t border-[var(--border-color)] overflow-hidden"
    >
      {/* Subtle lighting */}
      <div className="absolute top-1/3 left-1/4 w-[500px] h-[300px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[250px] bg-emerald-600/10 rounded-full blur-[130px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-950/40 border border-indigo-800/40 text-xs font-semibold text-indigo-300 mb-4 shadow-sm"
          >
            <CheckBadgeIcon className="w-4 h-4 text-indigo-400" />
            <span>Simple 3-Step Setup</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl md:text-5xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
          >
            SyncShift{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
              bridges the gap
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-4 text-sm sm:text-base text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            No complex setup. No manual calendar calculations. Go from scattered timetable files to 100% clash-free certainty in under 2 minutes.
          </motion.p>
        </div>

        {/* 3 Steps with Connected Line/Arrows */}
        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-10">
          {/* Animated Connecting Line on Desktop */}
          <div className="hidden md:block absolute top-28 left-[18%] right-[18%] h-0.5 z-0 pointer-events-none">
            <svg className="w-full h-8 overflow-visible" fill="none">
              <motion.path
                d="M 0,4 H 750"
                stroke="rgba(99, 102, 241, 0.25)"
                strokeWidth="2"
                strokeDasharray="6 6"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 1.2, ease: 'easeInOut' }}
              />
            </svg>
          </div>

          {STEPS.map((step, idx) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 35 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.6, delay: idx * 0.2 }}
                className="relative z-10 flex flex-col items-center md:items-start text-center md:text-left bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-7 sm:p-8 hover:bg-[var(--bg-secondary)] hover:border-[var(--border-hover)] transition-all duration-300 group"
              >
                {/* Step pill and icon header */}
                <div className="w-full flex items-center justify-between mb-6">
                  <div
                    className={`w-14 h-14 rounded-2xl ${step.bgColor} border ${step.borderColor} flex items-center justify-center shadow-lg transition-transform group-hover:scale-105 duration-300`}
                  >
                    <Icon className={`w-7 h-7 ${step.accentColor}`} />
                  </div>
                  <span className="font-mono text-xs font-bold px-3 py-1 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)]">
                    STEP {step.number}
                  </span>
                </div>

                <div className="space-y-3 w-full">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)] block">
                    {step.subtitle}
                  </span>
                  <h3 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
                    {step.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-[var(--text-secondary)] leading-relaxed">
                    {step.desc}
                  </p>
                </div>

                {/* Step badge pill at bottom */}
                <div className="mt-6 pt-4 border-t border-[var(--border-color)] w-full flex items-center justify-between text-[11px] text-[var(--text-muted)]">
                  <span>{step.tag}</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/60" />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
