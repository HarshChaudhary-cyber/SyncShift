'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import {academicRequest} from '@/lib/api';
import {useAuthContext} from '@/context/AuthContext';
export default function Page(){const {refreshUser,user}=useAuthContext();const router=useRouter();const [error,setError]=useState('');const [busy,setBusy]=useState(false);async function accept(){setBusy(true);try{await academicRequest('/academic-admin/accept','POST',{token:new URLSearchParams(window.location.search).get('token')});await refreshUser();router.replace('/dashboard');}catch(e){setError((e as Error).message);setBusy(false);}}return <section className="ws-panel"><h1>Join your university</h1><p>Accept the university invitation for {user?.email}. Only the invited account can use this link.</p>{error&&<p role="alert" className="notice error">{error}</p>}<button className="ws-button primary" disabled={busy} onClick={accept}>{busy?'Accepting…':'Accept invitation'}</button></section>;}
