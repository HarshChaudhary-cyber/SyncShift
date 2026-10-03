'use client';
import {useParams} from 'next/navigation';
import ProfilePage from '@/components/unified/ProfilePage';
export default function Page(){const {id}=useParams<{id:string}>();return <ProfilePage key={id} userId={id}/>;}
