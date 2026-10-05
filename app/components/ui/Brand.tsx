import Link from 'next/link';

export default function Brand({ href = '/', label = 'SyncShift home' }: { href?: string; label?: string }) {
  return <Link className="syncshift-brand" href={href} aria-label={label}>
    <span className="syncshift-mark" aria-hidden="true"><i /><i /><i /></span>
    SyncShift<span className="syncshift-dot">.</span>
  </Link>;
}
