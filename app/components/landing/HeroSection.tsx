'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowDownIcon, ArrowRightIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function HeroSection() {
  // Animation step: 0 = empty grid, 1 = class appears, 2 = shift appears, 3 = conflict detected
  const [animStep, setAnimStep] = useState(0);

  useEffect(() => {
    const cycle = () => {
      setAnimStep(1);
      const t1 = setTimeout(() => setAnimStep(2), 1200);
      const t2 = setTimeout(() => setAnimStep(3), 2400);
      const t3 = setTimeout(() => setAnimStep(0), 6500);
      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
        clearTimeout(t3);
      };
    };

    cycle();
    const interval = setInterval(cycle, 7200);
    return () => clearInterval(interval);
  }, []);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-screen flex flex-col justify-center items-center pt-24 pb-16 px-4 sm:px-6 lg:px-8 overflow-hidden bg-[var(--bg-primary)]">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] sm:w-[750px] h-[350px] sm:h-[450px] bg-indigo-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/3 right-10 w-[300px] h-[300px] bg-red-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border-color)_1px,transparent_1px),linear-gradient(to_bottom,var(--border-color)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] opacity-30 pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8 my-auto">
        {/* Top Tag Pill */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[11px] sm:text-xs font-semibold text-[var(--text-secondary)] shadow-xl"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Built for students balancing classes & part-time jobs</span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-[var(--text-primary)] leading-[1.1] max-w-4xl mx-auto"
        >
          Stop finding schedule conflicts{' '}
          <span className="bg-gradient-to-r from-red-400 via-rose-300 to-indigo-400 bg-clip-text text-transparent">
            the hard way.
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.25 }}
          className="text-base sm:text-lg lg:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto leading-relaxed"
        >
          Your university exports .ics files. Your job sends weekly rosters. SyncShift catches every clash before your semester starts.
        </motion.p>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2"
        >
          <Link
            href="/signup"
            className="w-full sm:w-auto px-7 py-3.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm sm:text-base flex items-center justify-center gap-2 shadow-xl shadow-indigo-600/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <span>Get Started Free</span>
            <ArrowRightIcon className="w-4 h-4" />
          </Link>
          <button
            onClick={() => scrollToSection('how-it-works')}
            className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-[var(--bg-secondary)] hover:bg-[var(--border-hover)] border border-[var(--border-color)] text-[var(--text-primary)] font-semibold text-sm sm:text-base flex items-center justify-center gap-2 transition-all hover:scale-[1.02] cursor-pointer"
          >
            <span>See How It Works</span>
            <ArrowDownIcon className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
        </motion.div>

        {/* Trust Badges */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.55 }}
          className="text-xs text-[var(--text-muted)] font-medium"
        >
          No registration required to try · Free forever
        </motion.p>

        {/* Interactive Simulated Calendar Visual */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.6 }}
          className="pt-6 sm:pt-10 max-w-2xl mx-auto w-full"
        >
          <div className="relative p-1 rounded-3xl bg-gradient-to-b from-neutral-700/50 via-neutral-800/20 to-neutral-900/60 shadow-2xl backdrop-blur-xl">
            <div className="bg-[var(--bg-card)] rounded-[22px] p-4 sm:p-6 border border-[var(--border-color)] relative overflow-hidden">
              {/* Header inside mockup */}
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-[var(--border-color)]">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  <span className="text-[11px] text-[var(--text-muted)] font-mono ml-2">Wednesday Schedule</span>
                </div>
                <div className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                  Live Clash Engine
                </div>
              </div>

              {/* Time grid container */}
              <div className="relative h-64 sm:h-72 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-color)] p-3 overflow-hidden flex flex-col justify-between">
                {/* Time markers */}
                <div className="absolute inset-0 flex flex-col justify-between p-3 pointer-events-none opacity-20">
                  {['09:00', '10:00', '11:00', '12:00', '13:00', '14:00'].map((time) => (
                    <div key={time} className="flex items-center gap-2 text-[10px] font-mono text-[var(--text-muted)] border-b border-[var(--border-color)] pb-1">
                      <span>{time}</span>
                    </div>
                  ))}
                </div>

                {/* Animated Blocks */}
                <div className="relative h-full flex gap-3 z-10 pt-2">
                  {/* Class block (Blue) */}
                  <div className="w-1/2 relative h-full">
                    <AnimatePresence>
                      {animStep >= 1 && (
                        <motion.div
                          initial={{ opacity: 0, y: -20 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ duration: 0.4 }}
                          className="absolute top-2 left-0 right-0 h-32 rounded-xl bg-blue-950/70 border-2 border-blue-500/80 p-3 shadow-lg shadow-blue-950/40 text-left"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase tracking-wider font-bold text-blue-400">
                              Lecture
                            </span>
                            <span className="text-[10px] text-blue-300 font-mono">09:00 - 10:30</span>
                          </div>
                          <div className="font-bold text-xs sm:text-sm text-white mt-1 truncate">
                            CS101: Data Structures
                          </div>
                          <div className="text-[11px] text-blue-300/80 mt-0.5">Hall B, Prof. Sharma</div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Work shift block (Green) */}
                  <div className="w-1/2 relative h-full">
                    <AnimatePresence>
                      {animStep >= 2 && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ duration: 0.4 }}
                          className="absolute top-16 left-0 right-0 h-44 rounded-xl bg-emerald-950/70 border-2 border-emerald-500/80 p-3 shadow-lg shadow-emerald-950/40 text-left"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase tracking-wider font-bold text-emerald-400">
                              Work Shift
                            </span>
                            <span className="text-[10px] text-emerald-300 font-mono">10:00 - 14:00</span>
                          </div>
                          <div className="font-bold text-xs sm:text-sm text-white mt-1 truncate">
                            Campus Library Desk
                          </div>
                          <div className="text-[11px] text-emerald-300/80 mt-0.5">Supervisor: Sarah ($17.50/h)</div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                {/* Overlap Clash Red Alert Badge */}
                <AnimatePresence>
                  {animStep >= 3 && (
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.8, opacity: 0 }}
                      transition={{ type: 'spring', stiffness: 350, damping: 20 }}
                      className="absolute top-20 left-1/2 -translate-x-1/2 z-30 px-4 py-2 rounded-xl bg-red-600/95 border-2 border-red-400 text-white shadow-[0_0_30px_rgba(239,68,68,0.7)] flex items-center gap-2"
                    >
                      <ExclamationTriangleIcon className="w-5 h-5 text-white animate-bounce" />
                      <div className="text-left">
                        <div className="text-[11px] font-black tracking-wide uppercase">
                          Conflict Detected!
                        </div>
                        <div className="text-[10px] text-red-100 font-medium">
                          30 min overlap between Lecture & Shift
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Status caption below mockup */}
              <div className="mt-3 flex items-center justify-between text-[11px] text-neutral-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-indigo-400" />
                  Auto-detects clashes across multiple formats
                </span>
                <span className="text-neutral-500 font-mono">Instant zero-delay alert</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
