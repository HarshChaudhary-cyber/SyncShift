'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {academicRequest,api,StudyTask} from '@/lib/api';
import {Teaching,Lecture} from '@/lib/academic';
import {useAuthContext} from '@/context/AuthContext';
import {formatTimeDisplay} from '@/lib/preferences';

export default function TeachingDashboard(){
  const {user} = useAuthContext();
  const [data,setData]=useState<Teaching>(); const [tasks,setTasks]=useState<StudyTask[]>([]); const [error,setError]=useState('');
  async function load(){try{const [d,t]=await Promise.all([academicRequest<Teaching>('/academic/teaching'),api.getTasks()]);setData(d);setTasks(t);setError('');}catch(e){setError((e as Error).message);}}
  useEffect(()=>{void load();const refresh=()=>void load();window.addEventListener('focus',refresh);return()=>window.removeEventListener('focus',refresh);},[]);
  function rows(sessions:Lecture[]){return sessions.length?sessions.map(s=><Link className="schedule-row" key={`${s.class_id}-${s.event_key}-${s.date}`} href={`/classes/${s.class_id}`}><div className="schedule-time">{formatTimeDisplay(s.start_time, user?.time_format)}<small>{formatTimeDisplay(s.end_time, user?.time_format)}</small></div><span className="schedule-marker"/><div><h3>{s.title}</h3><p>{s.date} · {s.class_name}</p></div><span className="ws-badge">{s.status}</span></Link>):<p className="ws-muted">No lectures scheduled in this period.</p>;}
  return <><header className="ws-header"><div><div className="ws-kicker">PROFESSOR WORKSPACE</div><h1>Your teaching day.</h1><p>{data?.today} · {data?.timezone} · Completion is recorded by teaching staff.</p></div><Link className="ws-button primary" href="/classes">Manage teaching classes</Link></header>
    {error&&<div role="alert" className="notice error">{error}<button onClick={load}>Retry</button></div>}
    {!data?<p role="status">Loading teaching schedule…</p>:<><div className="weekly-summary"><div><span>DELIVERED TODAY</span><strong>{data.completed_today}</strong></div><div><span>REMAINING TODAY</span><strong>{data.remaining_today}</strong></div><div><span>ASSIGNED CLASSES</span><strong>{data.classes.length}</strong></div></div>
      <div className="ws-grid"><section className="ws-panel"><h2>Today’s assigned lectures</h2>{rows(data.today_sessions)}<h2 style={{marginTop:28}}>Upcoming teaching</h2>{rows(data.upcoming)}</section><aside className="ws-stack"><section className="ws-panel"><h2>Preparation & private tasks</h2>{tasks.filter(t=>!['done','completed'].includes(t.status)).slice(0,6).map(t=><div className="ws-list-row" key={t.id}><strong>{t.title}</strong><p>Due {t.deadline} · {t.total_hours_required} hours</p></div>)}<Link className="ws-link" href="/planner">Plan preparation, grading and personal work →</Link></section><section className="ws-panel"><h2>Timetable & changes</h2><p className="ws-muted">Review official commitments alongside your private schedule.</p><Link href="/calendar" className="ws-link">Open calendar & conflicts →</Link><br/><Link href="/notifications" className="ws-link">Read timetable notifications →</Link></section></aside></div>
      <section style={{marginTop:28}}><h2>Subjects & teaching progress</h2><div className="class-grid">{data.classes.map(c=><Link className="ws-panel" key={c.id} href={`/classes/${c.id}`}><h2>{c.name}</h2><p>{c.subject.term || 'Term not supplied'}</p><strong>{c.progress.delivered_lectures} delivered · {c.progress.remaining_lectures} remaining</strong><p className="ws-muted">{c.progress.delivered_hours} recorded hours / {c.progress.planned_hours} planned hours</p></Link>)}</div></section></>}
  </>;
}
