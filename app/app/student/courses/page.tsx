'use client';

/**
 * Student Courses page — renders the existing student academics page
 * which shows enrolled courses and enrollment management.
 */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStudentAcademic } from '../layout';

export default function StudentCoursesPage() {
  const pathname = usePathname();
  const { institution, loading } = useStudentAcademic();

  const subTabs = [
    { label: 'Courses & Enrollments', href: '/student/courses', icon: '📚' },
    { label: 'Weekly Availability', href: '/student/availability', icon: '🕒' },
    { label: 'Constraints & Preferences', href: '/student/constraints', icon: '⚖️' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <svg width={32} height={32} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="animate-spin text-indigo-400" aria-hidden="true">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <p className="text-[var(--text-secondary)] text-sm">Loading courses…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🎓</span>
              <h1 className="text-xl font-black tracking-tight text-[var(--text-primary)]">
                My Academic Courses
              </h1>
              {institution && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {institution.name}
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Manage your enrolled university course sections, weekly availability, and scheduling preferences.
            </p>
          </div>

          {/* Sub-Navigation Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {subTabs.map((tab) => {
              const isActive = pathname === tab.href;
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/20'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Show a prompt if no institution */}
      {!institution && (
        <div className="p-4 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-2xl flex items-start gap-3">
          <span className="text-xl">⚠️</span>
          <div className="text-xs space-y-1">
            <div className="font-bold text-amber-800 dark:text-amber-300">No University Institution Linked</div>
            <p className="text-amber-900/80 dark:text-amber-200/80">
              Your account is not currently registered in an active institution. Please contact your academic department or registrar to enroll you in sections.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
