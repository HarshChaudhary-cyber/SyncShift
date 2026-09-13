'use client';

import React, { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ChatBubbleBottomCenterTextIcon, StarIcon } from '@heroicons/react/24/solid';

// Counter component that animates counting up from 0 when scrolled into view
function AnimatedCounter({
  target,
  duration = 1800,
  prefix = '',
  suffix = '',
}: {
  target: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });

  useEffect(() => {
    if (!isInView) return;

    let startTime: number | null = null;
    let frameId: number;

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeOut * target));

      if (progress < 1) {
        frameId = requestAnimationFrame(step);
      } else {
        setCount(target);
      }
    };

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [isInView, target, duration]);

  return (
    <span ref={ref} className="font-mono">
      {prefix}
      {count.toLocaleString()}
      {suffix}
    </span>
  );
}

const STATS = [
  {
    target: 2400,
    suffix: '+',
    label: 'Students Supported',
    subtext: 'Balancing coursework & jobs',
    color: 'from-indigo-400 to-cyan-400',
  },
  {
    target: 8,
    suffix: '',
    label: 'Universities Tested',
    subtext: 'Across Germany & Europe',
    color: 'from-emerald-400 to-teal-400',
  },
  {
    target: 12000,
    suffix: '+',
    label: 'Conflicts Caught',
    subtext: 'Zero missed seminars or shifts',
    color: 'from-rose-400 to-amber-400',
  },
];

const TESTIMONIALS = [
  {
    quote: 'Finally I don’t have to cross-check two Excel sheets manually. SyncShift instantly imported my university .ics and caught a clash with my barista shift.',
    author: 'Leonhard K.',
    role: 'CS @ TU Munich',
    detail: 'Part-time Café Barista (16h/wk)',
    initials: 'LK',
    avatarBg: 'from-blue-600 to-indigo-600',
  },
  {
    quote: 'Saved me from registering for a mandatory seminar during my highest-paying research assistant shift. The what-if drag tester is a lifesaver.',
    author: 'Ananya R.',
    role: 'M.Sc. Biotech @ Heidelberg',
    detail: 'HiWi Student Assistant (12h/wk)',
    initials: 'AR',
    avatarBg: 'from-emerald-600 to-teal-600',
  },
  {
    quote: 'The conflict alert showed up before I even noticed the clash. That pulsing red warning stopped me from getting penalized for missed lab hours.',
    author: 'Sophie M.',
    role: 'Business Informatics @ RWTH Aachen',
    detail: 'Retail Associate (15h/wk)',
    initials: 'SM',
    avatarBg: 'from-rose-600 to-pink-600',
  },
];

export default function StatsAndTestimonials() {
  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6 lg:px-8 bg-[var(--bg-secondary)] border-t border-[var(--border-color)] overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-indigo-950/20 rounded-full blur-[160px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto space-y-20 sm:space-y-28">
        {/* Stats Row */}
        <div>
          <div className="text-center max-w-3xl mx-auto mb-12">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] mb-4"
            >
              <span>Impact by the Numbers</span>
            </motion.div>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="text-3xl sm:text-4xl font-black text-[var(--text-primary)] tracking-tight"
            >
              Built to protect your grades and your paycheck
            </motion.h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            {STATS.map((stat, idx) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: idx * 0.15 }}
                className="relative rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-8 text-center flex flex-col items-center justify-center hover:bg-[var(--bg-secondary)] transition-all group"
              >
                <div
                  className={`text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight bg-gradient-to-r ${stat.color} bg-clip-text text-transparent mb-2`}
                >
                  <AnimatedCounter target={stat.target} suffix={stat.suffix} />
                </div>
                <div className="text-base font-bold text-[var(--text-primary)] mb-1">
                  {stat.label}
                </div>
                <div className="text-xs text-[var(--text-secondary)]">
                  {stat.subtext}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Testimonials */}
        <div>
          <div className="text-center max-w-2xl mx-auto mb-14">
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] mb-3"
            >
              <ChatBubbleBottomCenterTextIcon className="w-4 h-4 text-indigo-400" />
              <span>Student Experiences</span>
            </motion.div>
            <motion.h3
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="text-2xl sm:text-3xl font-black text-[var(--text-primary)] tracking-tight"
            >
              Loved by student workers everywhere
            </motion.h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {TESTIMONIALS.map((item, idx) => (
              <motion.div
                key={item.author}
                initial={{ opacity: 0, y: 35 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: idx * 0.15 }}
                className="relative rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] p-7 flex flex-col justify-between hover:bg-[var(--bg-secondary)] transition-all duration-300 group"
              >
                <div className="space-y-4">
                  {/* Star rating */}
                  <div className="flex items-center gap-1 text-amber-400">
                    {[...Array(5)].map((_, i) => (
                      <StarIcon key={i} className="w-4 h-4" />
                    ))}
                  </div>

                  <p className="text-sm text-[var(--text-secondary)] italic leading-relaxed">
                    "{item.quote}"
                  </p>
                </div>

                <div className="mt-6 pt-5 border-t border-[var(--border-color)] flex items-center gap-3.5">
                  <div
                    className={`w-10 h-10 rounded-full bg-gradient-to-tr ${item.avatarBg} flex items-center justify-center text-white text-xs font-bold shadow-md`}
                  >
                    {item.initials}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[var(--text-primary)]">
                      {item.author}
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)]">
                      {item.role}
                    </div>
                    <div className="text-[10px] text-[var(--text-muted)] font-medium">
                      {item.detail}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
