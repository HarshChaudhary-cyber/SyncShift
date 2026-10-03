'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
export default function LegacyRedirect({to}: {to: string}) {
 const router = useRouter();
 useEffect(() => { router.replace(to + window.location.search); }, [to, router]);
 return <p role="status" className="ws-muted">Opening your workspace…</p>;
}
