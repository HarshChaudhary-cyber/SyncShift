'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AcademicCapIcon, PlusIcon, ArrowRightIcon } from '@heroicons/react/24/outline';
import { api, AcademicCourse } from '@/lib/api';
import {isProfessor} from '@/lib/academic';
import { useAuthContext } from '@/context/AuthContext';
import Modal from './Modal';

export default function Classes() {
  const {user,memberships, refreshUser, error: sessionError} = useAuthContext();
  const teaching=isProfessor(user?.institution_role)||['admin','super_admin'].includes(user?.institution_role||'');
  const [courses,setCourses]=useState<AcademicCourse[]>([]); const [courseId,setCourseId]=useState('');
  useEffect(()=>{if(teaching&&user?.institution_id)api.getAcademicCourses(user.institution_id).then(setCourses).catch(()=>setCourses([]));},[teaching,user?.institution_id]);
  const router = useRouter();

  const [mode, setMode] = useState<'create' | 'join' | 'invite' | null>(null);
  const [name, setName] = useState(''); const [description, setDescription] = useState('');
  const [code, setCode] = useState(''); const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  useEffect(() => {const invitation = new URLSearchParams(window.location.search).get('invite'); if(invitation) {setToken(invitation); setMode('invite');}}, []);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const data = mode === 'create' ? await api.createClass(name, description,user?.institution_id||undefined,Number(courseId)) : mode === 'invite' ? await api.acceptClassInvitation(token) : await api.joinClass(code);
      await refreshUser(); router.push(`/classes/${data.id}`);
    } catch (e) {setError(e instanceof Error ? e.message : 'Could not update your classes.');} finally {setBusy(false);}
  }
  const visible = memberships.filter(c => teaching ? c.role==='instructor' : c.role==='learner');
  return <><header className="ws-header"><div><div className="ws-kicker">{teaching?'TEACHING':'YOUR SUBJECTS'}</div><h1>{teaching?'Teaching classes':'Classes & subjects'}</h1><p>{teaching?'Manage your assigned subjects, sections and lectures.':'Official university classes alongside your private schedule.'}</p></div><div className="ws-actions">{teaching?<button className="ws-button primary" onClick={()=>{setMode('create');setError('');}}><PlusIcon/>Create class</button>:<button className="ws-button" onClick={()=>{setMode('join');setError('');}}>Join a class</button>}</div></header>    {sessionError && <div className="notice error">Classes could not be refreshed.<button onClick={refreshUser}>Retry</button></div>}
    <div className="class-grid">{visible.map(c => <Link key={c.id} href={`/classes/${c.id}`} className="ws-panel class-tile"><span className="class-icon"><AcademicCapIcon/></span><h2>{c.name}</h2><p>{c.description || 'Timetable, announcements and your class community.'}</p><footer><span className="ws-badge accent">{c.role === 'instructor' ? 'Instructor' : 'Learner'}</span><ArrowRightIcon/></footer></Link>)}</div>
    {!visible.length && <div className="ws-panel ws-empty"><h2>No assigned classes yet.</h2><p>Your administrator can assign your subjects and sections.</p><button className="ws-button" style={{marginTop:18}} onClick={() => setMode('join')}>Join your first class</button></div>}
    <p className="ws-muted" style={{marginTop:25,fontSize:12}}>Teaching permissions come from your university assignments. Your private calendar is never shared with classmates or instructors.</p>
    {mode && <Modal title={mode==='create' ? 'Create a class' : mode==='invite' ? 'Accept class invitation' : 'Join a class'} onClose={() => setMode(null)}><form onSubmit={submit} className="ws-form">
      {mode==='create' ? <><label>Class name<input autoFocus value={name} onChange={e=>setName(e.target.value)} required maxLength={160} placeholder="e.g. Introduction to Design"/></label><label>Description<textarea value={description} onChange={e=>setDescription(e.target.value)} maxLength={4000} placeholder="What will you learn together?"/></label><label>Authorized subject<select required value={courseId} onChange={e=>setCourseId(e.target.value)}><option value="">Select subject</option>{courses.filter(c=>!isProfessor(user?.institution_role)||memberships.some(m=>m.role==='instructor'&&m.course_id===c.id)).map(c=><option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label><p className="ws-muted">Only subjects assigned to you can be used.</p></> : mode==='join' ? <><label>Class code<input autoFocus value={code} onChange={e=>setCode(e.target.value)} required placeholder="Enter the code from your instructor"/></label><p className="ws-muted">A class code grants learner access only.</p><button type="button" className="ws-link" onClick={() => setMode('invite')}>I have an invitation token instead</button></> : <><label>Invitation token<input value={token} onChange={e=>setToken(e.target.value)} required/></label><p className="ws-muted">Invitations are tied to your account email and expire after seven days.</p></>}
      {error && <p role="alert" className="notice error">{error}</p>}<button disabled={busy} className="ws-button primary">{busy ? 'Saving…' : mode==='create' ? 'Create class' : mode==='join' ? 'Join as learner' : 'Accept invitation'}</button>
    </form></Modal>}
  </>;
}
