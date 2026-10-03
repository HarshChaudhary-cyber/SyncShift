'use client';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { PlusIcon, ArrowUpTrayIcon, ArrowRightIcon, ClockIcon } from '@heroicons/react/24/outline';
import { api, DashboardData, StudyTask } from '@/lib/api';
import { useAuthContext } from '@/context/AuthContext';
import { CalendarProvider } from '@/context/CalendarContext';
import BlockModal from '@/components/calendar/BlockModal';
import ImportModal from '@/components/calendar/ImportModal';
import { showSuccessToast } from '@/lib/toast';
import TeachingDashboard from './TeachingDashboard';
import AdminArea from './AdminArea';
import {isProfessor} from '@/lib/academic';

function DashboardContent() {
  const {user, memberships} = useAuthContext();
  const [data, setData] = useState<DashboardData | null>(null);
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [eventOpen, setEventOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { const [overview, deadlines] = await Promise.all([api.getDashboard(), api.getTasks()]); setData(overview); setTasks(deadlines); }
    catch(e) { setError(e instanceof Error ? e.message : 'Could not load your schedule.'); }
    finally {setLoading(false);}
  }, []);
  useEffect(() => {void load(); const refresh = () => void load(); window.addEventListener('syncshift:schedule-updated', refresh); window.addEventListener('focus', refresh); return () => {window.removeEventListener('syncshift:schedule-updated', refresh); window.removeEventListener('focus', refresh);};}, [load]);
  const pending = tasks.filter(t => !['completed','done'].includes(t.status)).sort((a,b) => a.deadline.localeCompare(b.deadline)).slice(0,3);
  return <>
    <header className="ws-header"><div><div className="ws-kicker">{data ? new Date(data.today.date+'T12:00:00').toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'}) : 'Your daily overview'}</div><h1>Your day, in sync.</h1><p>Welcome back{user?.display_name ? `, ${user.display_name.split(' ')[0]}` : ''}. Make room for what matters.</p></div><div className="ws-actions"><button className="ws-button" onClick={() => setImportOpen(true)}><ArrowUpTrayIcon/>Import timetable</button><button className="ws-button primary" onClick={() => setEventOpen(true)}><PlusIcon/>Add event</button></div></header>
    {error && <div className="notice error" role="alert">{error}<button onClick={load}>Retry</button></div>}
    {loading && !data ? <div className="ws-panel ws-empty" role="status">Loading your schedule…</div> : data && <>
      <div className="weekly-summary" aria-label="Weekly hours"><div><span>CLASS TIME · THIS WEEK</span><strong>{data.week.total_class_hours} <span>hrs</span></strong></div><div><span>WORK TIME</span><strong>{data.week.total_shift_hours} <span>/ {data.week.work_limit} hrs</span></strong></div><div><span>PLANNED STUDY</span><strong>{data.study?.planned_hours ?? 0} <span>hrs</span></strong></div></div>
      <div className="ws-grid"><section className="ws-panel"><div className="ws-panel-header"><h2>Today’s schedule</h2><Link className="ws-link" href="/calendar">View calendar →</Link></div>
        {data.today.blocks.length === 0 ? <div className="ws-empty"><h2>A little breathing room.</h2><p>You have no events scheduled today.</p><button className="ws-button" onClick={() => setEventOpen(true)}>Plan your day</button></div> : data.today.blocks.map((event, index) => <div className="schedule-row" key={`${event.id}-${index}`}><div className="schedule-time">{event.start_time.slice(0,5)}<small>{event.end_time.slice(0,5)}</small></div><span className={`schedule-marker ${event.type}`}/><div><h3>{event.title}</h3><p>{event.location || (event.type === 'shift' ? 'Work shift' : event.type === 'study' ? 'Study session' : 'Class')}</p></div><span className={`ws-badge ${event.id < 0 ? 'accent' : ''}`}>{event.source === 'shared_class' ? 'University-managed' : 'Private'}</span></div>)}
        <div className="ws-panel-header" style={{marginTop:28,marginBottom:0}}><p className="ws-muted" style={{fontSize:12}}>Your work and personal plans are visible only to you.</p></div>
      </section><aside className="ws-stack"><section className="ws-panel"><div className="ws-panel-header"><h2>Up next</h2><ClockIcon/></div>{data.next_up ? <><span className="ws-badge accent">{data.next_up.label}</span><div className="ws-next-time">{data.next_up.block.start_time.slice(0,5)} <small>{data.next_up.block.occurrence_date}</small></div><h3>{data.next_up.block.title}</h3><p className="ws-muted">{data.next_up.block.location}</p></> : <p className="ws-muted">Nothing coming up. Enjoy the free time.</p>}</section>
        <section className="ws-panel"><div className="ws-panel-header"><h2>Upcoming deadlines</h2><Link href="/planner" aria-label="Open planner"><ArrowRightIcon/></Link></div>{pending.length ? pending.map(task => <div key={task.id} className="ws-list-row"><strong>{task.title}</strong><p>Due {task.deadline} · {task.total_hours_required} hours</p></div>) : <p className="ws-muted">No pending deadlines. Add a task in Planner.</p>}</section>
        {data.alerts.length > 0 && <section className="ws-panel"><h2>Needs your attention</h2>{data.alerts.slice(0,3).map((alert,index) => <div key={index} className="ws-list-row"><p>{alert.message}</p><Link className="ws-link" href="/calendar">Review in calendar →</Link></div>)}</section>}
      </aside></div>
      <section style={{marginTop:32}}><div className="ws-panel-header"><h2>Your classes</h2><Link className="ws-link" href="/classes">All classes →</Link></div><div className="class-grid">{memberships.slice(0,3).map(c => <Link className="ws-panel" href={`/classes/${c.id}`} key={c.id}><span className="ws-badge">{c.role === 'instructor' ? 'Teaching' : 'Learning'}</span><h2 style={{marginTop:12}}>{c.name}</h2></Link>)}{!memberships.length && <div className="ws-panel ws-muted">Join a class to see its timetable alongside your private schedule. <Link className="ws-link" href="/classes">Explore classes →</Link></div>}</div></section>
    </>}
    <BlockModal isOpen={eventOpen} onClose={() => {setEventOpen(false); void load();}} defaultType="shift"/>
    <ImportModal isOpen={importOpen} onClose={() => {setImportOpen(false); void load();}} onToast={showSuccessToast}/>
  </>;
}
export default function Dashboard() { const {user}=useAuthContext(); if(user?.institution_role==='super_admin') return <AdminArea/>; if(isProfessor(user?.institution_role)) return <TeachingDashboard/>; return <CalendarProvider><DashboardContent/></CalendarProvider>; }
