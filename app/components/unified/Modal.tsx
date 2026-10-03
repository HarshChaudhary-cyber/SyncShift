'use client';
import { useEffect, useRef, useId } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
export default function Modal({title, children, onClose}: {title: string; children: React.ReactNode; onClose: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className="ws-dialog" aria-labelledby={titleId} onCancel={onClose}><header><h2 id={titleId}>{title}</h2><button aria-label="Close dialog" onClick={onClose}><XMarkIcon/></button></header>{children}</dialog>;
}
