'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { MotionConfig } from 'framer-motion';
import { Squares2X2Icon, CalendarDaysIcon, AcademicCapIcon, ClipboardDocumentListIcon, BellIcon, SparklesIcon, Bars3Icon, XMarkIcon, ChevronDownIcon, Cog6ToothIcon, UsersIcon, BuildingOfficeIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { useAuthContext } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import { openSyncShiftAssistant } from '@/components/assistant/SyncShiftAssistant';
import { isReducedMotionActive } from '@/lib/preferences';
import './workspace.css';
import Brand from '@/components/ui/Brand';

const navigation = [
  ['Dashboard', '/dashboard', Squares2X2Icon], ['Calendar', '/calendar', CalendarDaysIcon],
  ['Classes', '/classes', AcademicCapIcon], ['Planner', '/planner', ClipboardDocumentListIcon], ['Notifications', '/notifications', BellIcon],
  ['Settings', '/settings', Cog6ToothIcon],
] as const;
const adminNavigation = [
  ['Overview & users','/admin',Squares2X2Icon],['Subjects','/university/courses',AcademicCapIcon],
  ['Sections & assignments','/university/sections',ClipboardDocumentListIcon],['Timetables','/university/timetables',CalendarDaysIcon],
  ['Faculty','/university/faculty',UsersIcon],['Rooms','/university/rooms',BuildingOfficeIcon],
  ['Departments','/university/departments',AcademicCapIcon],['Academic terms','/university/terms',CalendarDaysIcon],
  ['Institutional settings', '/university/settings', Cog6ToothIcon],['Audit history','/university/audit-logs',DocumentTextIcon],
] as const;

export default function AppShell({ children }: {children: React.ReactNode}) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const {user, logout, error, refreshUser} = useAuthContext();
  const [isReduced, setIsReduced] = useState(() => isReducedMotionActive(user?.reduced_motion));

  useEffect(() => {
    setIsReduced(isReducedMotionActive(user?.reduced_motion));
    const handleMotionChange = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (typeof detail?.active === 'boolean') {
        setIsReduced(detail.active);
      }
    };
    window.addEventListener('syncshift:reduced-motion-change', handleMotionChange);
    return () => window.removeEventListener('syncshift:reduced-motion-change', handleMotionChange);
  }, [user?.reduced_motion]);

  const management=user?.institution_role==='super_admin'&&(pathname==='/dashboard'||pathname.startsWith('/admin')||pathname.startsWith('/university'));
  return <ProtectedRoute><MotionConfig reducedMotion={isReduced ? 'always' : 'never'}><div className="workspace-app">
    <a className="skip-link" href="#workspace-content">Skip to content</a>
    <header className="mobile-bar"><Brand href="/dashboard" label="SyncShift dashboard" /><button aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={mobileOpen} onClick={() => setMobileOpen(!mobileOpen)}>{mobileOpen ? <XMarkIcon/> : <Bars3Icon/>}</button></header>
    {mobileOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)}/>}
    <aside className={`workspace-sidebar ${mobileOpen ? 'is-open' : ''}`}>
      <Brand href="/dashboard" label="SyncShift dashboard" />
      <p className="sidebar-caption">{management?'UNIVERSITY MANAGEMENT':'YOUR WORKSPACE'}</p>
      <nav aria-label="Main navigation">{(management?adminNavigation:navigation).map(([name, href, Icon]) => <Link key={href} href={href} aria-current={pathname.startsWith(href) ? 'page' : undefined} onClick={() => setMobileOpen(false)}><Icon/><span>{name}</span></Link>)}</nav>
      {management&&<Link className="ws-button" href="/calendar" onClick={()=>setMobileOpen(false)}>My private workspace</Link>}
      {user?.institution_role==='super_admin'&&<Link className="ws-button" href="/admin" onClick={()=>setMobileOpen(false)}>University administration</Link>}
      <div className="sidebar-bottom"><button className="assistant-entry" onClick={() => {openSyncShiftAssistant(); setMobileOpen(false);}}><SparklesIcon/><span>Ask SyncShift</span><kbd>AI</kbd></button>
        <details className="account-menu"><summary><span className="avatar">{(user?.display_name || user?.email || 'S').slice(0,1).toUpperCase()}</span><span className="account-name">{user?.display_name || 'Your account'}<small>Account & preferences</small></span><ChevronDownIcon/></summary>
          <div><Link href="/profile" onClick={() => setMobileOpen(false)}>My profile</Link><Link href="/settings" onClick={() => setMobileOpen(false)}>Account settings</Link><Link href="/settings?tab=preferences" onClick={() => setMobileOpen(false)}>Preferences</Link>
            {['admin','super_admin','faculty','professor'].includes(user?.institution_role || '') && <Link href="/university/resources">Advanced administration</Link>}
            <button onClick={logout}>Sign out</button></div>
        </details>
      </div>
    </aside>
    <main id="workspace-content" className="workspace-content" tabIndex={-1}>{error && <div className="notice" role="status">{error}<button onClick={refreshUser}>Retry verification</button></div>}{children}</main>
  </div></MotionConfig></ProtectedRoute>;
}

export function ApplicationBoundary({children}: {children: React.ReactNode}) {
  const path = usePathname();
  const unified = ['/dashboard','/calendar','/classes','/planner','/notifications','/settings','/student','/profile','/professors','/admin','/appointments','/invitation'].some(prefix => path === prefix || path.startsWith(prefix + '/'));
  return unified ? <AppShell>{children}</AppShell> : <>{children}</>;
}
