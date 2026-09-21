'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRightIcon, SparklesIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

export default function CtaSection() {
  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-card)] border-t border-[var(--border-color)] overflow-hidden">
      {/* Glow highlight */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-indigo-600/20 rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[250px] bg-rose-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative max-w-4xl mx-auto text-center space-y-8">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] shadow-md"
        >
          <SparklesIcon className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <span>Start the semester stress-free</span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="text-3xl sm:text-5xl lg:text-6xl font-black text-[var(--text-primary)] tracking-tight leading-tight"
        >
          Ready to stop{' '}
          <span className="bg-gradient-to-r from-indigo-400 via-rose-300 to-amber-300 bg-clip-text text-transparent">
            double-checking calendars?
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-base sm:text-lg text-[var(--text-secondary)] max-w-xl mx-auto leading-relaxed"
        >
          Join thousands of university students who never worry about course overlaps, missed work shifts, or visa hour limits.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2"
        >
          <Link
            href="/signup"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-black text-sm sm:text-base tracking-tight shadow-xl hover:shadow-2xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] group cursor-pointer"
          >
            <span>Create Free Account</span>
            <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex items-center justify-center gap-2 text-xs text-[var(--text-secondary)]"
        >
          <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
          <span>Takes 30 seconds · No credit card · Free forever</span>
        </motion.div>
      </div>
    </section>
  );
}
