'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  FolderIcon,
  BookOpenIcon,
  ClipboardDocumentListIcon,
  AcademicCapIcon,
  BuildingOfficeIcon,
  BuildingOffice2Icon,
  CalendarDaysIcon,
} from '@heroicons/react/24/outline';

export default function AcademicResourcesNav() {
  const pathname = usePathname();

  const resourceItems = [
    { label: 'All Resources', href: '/university/resources', icon: <FolderIcon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Courses', href: '/university/courses', icon: <BookOpenIcon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Sections', href: '/university/sections', icon: <ClipboardDocumentListIcon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Faculty', href: '/university/faculty', icon: <AcademicCapIcon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Rooms', href: '/university/rooms', icon: <BuildingOfficeIcon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Departments', href: '/university/departments', icon: <BuildingOffice2Icon className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Academic Terms', href: '/university/terms', icon: <CalendarDaysIcon className="w-4 h-4" aria-hidden="true" /> },
  ];

  return (
    <nav
      aria-label="Academic Resources Sub-navigation"
      className="mb-6 p-1.5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-xs"
    >
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-0.5">
        <div className="hidden md:flex items-center px-3 text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] shrink-0 border-r border-[var(--border-color)] mr-1">
          Academic Resources
        </div>
        {resourceItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all shrink-0 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-900/30'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
