'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircleIcon, AcademicCapIcon, BuildingLibraryIcon } from '@heroicons/react/24/outline';

const STUDENT_BENEFITS = [
  {
    title: 'Import from HISinOne, C@MPUS, or any .ics',
    desc: 'Works seamlessly with standard German university portals including HISinOne, C@MPUS, RWTHonline, and Moodle iCal feeds.',
  },
  {
    title: 'Track your 20h/week visa work limit',
    desc: 'Strict Werkstudentenprivileg and international student visa caps are monitored live with automatic warnings before you breach the 20-hour limit.',
  },
  {
    title: 'See your weekly earnings estimate',
    desc: 'Accurately calculate gross income from your Minijob (€538) or Werkstudent wage across shifting weekly schedules.',
  },
  {
    title: 'Sunday midnight week-split intelligence',
    desc: 'Overnight shifts crossing Sunday 24:00 are automatically divided across calendar weeks to safeguard immigration compliance.',
  },
];

const UNI_BENEFITS = [
  {
    title: 'Works with any timetable export format',
    desc: 'Compatible with standard .ics feeds, PDF schedules, screenshot timetable uploads, and manual recurring block entry.',
  },
  {
    title: 'Understands German semester schedules',
    desc: 'Pre-configured for Sommersemester and Wintersemester timelines, Vorlesungszeit dates, and holiday reading weeks.',
  },
  {
    title: 'Timezone-aware local clocking',
    desc: 'Respects Europe/Berlin and continental daylight savings automatically, keeping class reminders accurate year-round.',
  },
  {
    title: 'Academic quarter (c.t. / s.t.) friendly',
    desc: 'Flexible start and end times allow exact 15-minute alignment with cum tempore (c.t.) university lecture traditions.',
  },
];

export default function EuropeSection() {
  return (
    <section
      id="europe"
      className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-secondary)] border-t border-[var(--border-color)] overflow-hidden"
    >
      {/* Ambient lighting */}
      <div className="absolute top-1/2 left-1/3 w-[600px] h-[350px] bg-indigo-900/10 rounded-full blur-[160px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 sm:mb-20">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] mb-4 shadow-sm"
          >
            <span>🇩🇪 🇬🇧 🇪🇺 Built for Europe & International Students</span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl md:text-5xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
          >
            Built for students studying and{' '}
            <span className="bg-gradient-to-r from-amber-400 via-rose-300 to-indigo-400 bg-clip-text text-transparent">
              working in Europe
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-4 text-sm sm:text-base text-[var(--text-secondary)] max-w-2xl mx-auto"
          >
            From Berlin to Munich, Stuttgart to Aachen: tailored to international students balancing Werkstudent contracts or Minijobs with intensive university curricula.
          </motion.p>
        </div>

        {/* Two Columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
          {/* Left Column: For Students */}
          <motion.div
            initial={{ opacity: 0, x: -25 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6 }}
            className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-7 sm:p-8 hover:bg-[var(--bg-secondary)] transition-all duration-300 relative overflow-hidden group"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
                <AcademicCapIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
                  For Student Workers
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Protect your visa, study credits & earnings
                </p>
              </div>
            </div>

            <ul className="space-y-4">
              {STUDENT_BENEFITS.map((item) => (
                <li key={item.title} className="flex items-start gap-3">
                  <CheckCircleIcon className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-sm font-bold text-[var(--text-primary)]">
                      {item.title}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)] mt-0.5 leading-relaxed">
                      {item.desc}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Right Column: For German Universities */}
          <motion.div
            initial={{ opacity: 0, x: 25 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.6 }}
            className="rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-7 sm:p-8 hover:bg-[var(--bg-secondary)] transition-all duration-300 relative overflow-hidden group"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
                <BuildingLibraryIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
                  For German Universities & Systems
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Built to parse European academic systems
                </p>
              </div>
            </div>

            <ul className="space-y-4">
              {UNI_BENEFITS.map((item) => (
                <li key={item.title} className="flex items-start gap-3">
                  <CheckCircleIcon className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-sm font-bold text-[var(--text-primary)]">
                      {item.title}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)] mt-0.5 leading-relaxed">
                      {item.desc}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
