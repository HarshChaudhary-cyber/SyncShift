'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useUniversity } from '../layout';
import AcademicResourcesNav from '@/components/university/AcademicResourcesNav';
import { api } from '@/lib/api';

interface ResourceCounts {
  courses: number | null;
  sections: number | null;
  faculty: number | null;
  rooms: number | null;
  departments: number | null;
  terms: number | null;
}

export default function AcademicResourcesHubPage() {
  const { institution, isAdmin } = useUniversity();
  const [counts, setCounts] = useState<ResourceCounts>({
    courses: null,
    sections: null,
    faculty: null,
    rooms: null,
    departments: null,
    terms: null,
  });
  const [loading, setLoading] = useState(true);

  const loadCounts = useCallback(async () => {
    if (!institution) return;
    try {
      setLoading(true);
      const [c, s, f, r, d, t] = await Promise.allSettled([
        api.getAcademicCourses(institution.id),
        api.getSections(institution.id),
        api.getFaculty(institution.id),
        api.getRooms(institution.id),
        api.getDepartments(institution.id),
        api.getAcademicTerms(institution.id),
      ]);

      setCounts({
        courses: c.status === 'fulfilled' ? c.value.length : null,
        sections: s.status === 'fulfilled' ? s.value.length : null,
        faculty: f.status === 'fulfilled' ? f.value.length : null,
        rooms: r.status === 'fulfilled' ? r.value.length : null,
        departments: d.status === 'fulfilled' ? d.value.length : null,
        terms: t.status === 'fulfilled' ? t.value.length : null,
      });
    } finally {
      setLoading(false);
    }
  }, [institution]);

  useEffect(() => {
    loadCounts();
  }, [loadCounts]);

  const cards = [
    {
      title: 'Courses',
      icon: '📚',
      count: counts.courses,
      unit: 'Courses',
      href: '/university/courses',
      description: 'Define course catalog, credit requirements, instructional levels, and minimum room requirements.',
      actionText: 'Manage Courses',
      badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    },
    {
      title: 'Sections',
      icon: '📑',
      count: counts.sections,
      unit: 'Sections',
      href: '/university/sections',
      description: 'Configure course class sections, student seating capacities, and assign teaching instructors.',
      actionText: 'Manage Sections',
      badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    },
    {
      title: 'Faculty',
      icon: '👨‍🏫',
      count: counts.faculty,
      unit: 'Instructors',
      href: '/university/faculty',
      description: 'Maintain academic staff records, faculty designations, and departmental teaching appointments.',
      actionText: 'Manage Faculty',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    },
    {
      title: 'Rooms',
      icon: '🚪',
      count: counts.rooms,
      unit: 'Rooms',
      href: '/university/rooms',
      description: 'Organize classrooms, lecture halls, and specialized labs with seating capacities and equipment.',
      actionText: 'Manage Rooms',
      badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    },
    {
      title: 'Departments',
      icon: '🏢',
      count: counts.departments,
      unit: 'Departments',
      href: '/university/departments',
      description: 'Structure academic faculties, subject divisions, departmental leadership, and budget units.',
      actionText: 'Manage Departments',
      badgeColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    },
    {
      title: 'Academic Terms',
      icon: '📅',
      count: counts.terms,
      unit: 'Terms',
      href: '/university/terms',
      description: 'Define institutional semesters, quarters, start/end dates, and active scheduling terms.',
      actionText: 'Manage Terms',
      badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Secondary Pill Subnavigation */}
      <AcademicResourcesNav />

      {/* Hero / Page Purpose Header */}
      <div className="bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-transparent border border-indigo-500/20 rounded-2xl p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold tracking-wide">
              <span>🏛️</span> University Master Building Blocks
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)]">
              Academic Resources
            </h1>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              These are the foundational elements used to build your university&apos;s timetable.
              Configure courses, sections, instructors, rooms, and terms here to supply the baseline requirements
              for automated conflict detection and student scheduling.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <Link
              href="/university/timetables"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-sm"
            >
              <span>🗓️</span>
              <span>Go to Timetables</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 6 Core Resource Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {cards.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="group relative flex flex-col justify-between p-6 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-indigo-500/50 hover:bg-[var(--bg-hover)] transition-all shadow-xs hover:shadow-md"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-4">
                <span className="text-3xl p-2.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-color)]">
                  {card.icon}
                </span>
                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${card.badgeColor}`}
                >
                  {loading ? '…' : card.count !== null ? `${card.count} ${card.unit}` : 'Configured'}
                </span>
              </div>

              <h2 className="text-lg font-bold text-[var(--text-primary)] group-hover:text-indigo-400 transition-colors">
                {card.title}
              </h2>

              <p className="text-xs text-[var(--text-secondary)] mt-2 leading-relaxed">
                {card.description}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-[var(--border-subtle)] flex items-center justify-between text-xs font-semibold text-indigo-400 group-hover:text-indigo-300 transition">
              <span>{card.actionText}</span>
              <span className="transform group-hover:translate-x-1 transition-transform">→</span>
            </div>
          </Link>
        ))}
      </div>

      {/* Contextual Guide Card */}
      <div className="p-5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] text-xs text-[var(--text-secondary)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="text-xl">💡</span>
          <div>
            <span className="font-semibold text-[var(--text-primary)] block mb-0.5">
              How Academic Resources connect to Timetables
            </span>
            <span>
              Each <strong>Timetable Meeting</strong> pairs an enrolled <strong>Course Section</strong> with an assigned <strong>Faculty Instructor</strong>, reserved <strong>Room</strong>, and scheduled day/time. SyncShift automatically ensures no room or instructor is double-booked.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
