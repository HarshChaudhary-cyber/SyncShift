'use client';

import React, { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ClockIcon, ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline';

export interface TimePickerProps {
  value?: string; // HH:MM, in 24-hour time
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
  id?: string;
  name?: string;
  min?: string;
  max?: string;
  label?: string;
}

const isTime = (time: string) => /^([01]\d|2[0-3]):[0-5]\d$/.test(time);
const pad = (number: number) => String(number).padStart(2, '0');
const control = 'min-h-11 rounded-lg px-3 border border-[var(--border-color)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--brand-accent)]';
const active = 'bg-[var(--accent-primary)] text-white';

export default function TimePicker({
  value = '', onChange, placeholder = 'Select time', disabled = false,
  error = false, className = '', id, name, min, max, label = 'Time',
}: TimePickerProps) {
  const popupId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState('09:00');
  const [mode, setMode] = useState<'hour' | 'minute'>('hour');
  const [message, setMessage] = useState('');
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const hourRef = useRef<HTMLButtonElement>(null);
  const minuteRef = useRef<HTMLButtonElement>(null);
  const [bounds, setBounds] = useState({ left: 12, top: 12, width: 304, maxHeight: 480 });
  const [hour, minute] = (isTime(draft) ? draft : '09:00').split(':').map(Number);
  const hour12 = hour % 12 || 12;
  const selected = mode === 'hour' ? hour12 % 12 : minute / 5;

  function close() {
    setIsOpen(false);
    triggerRef.current?.focus({ preventScroll: true });
  }

  function apply() {
    const time = draft.trim();
    if (!isTime(time)) {
      setMessage('Enter a time from 00:00 to 23:59.');
      return;
    }
    // Like a native time input, a range crossing midnight allows either side.
    const outside = min && max && min > max
      ? time < min && time > max
      : (min && time < min) || (max && time > max);
    if (outside) {
      setMessage(`Choose a time ${min ? `from ${min}` : ''}${max ? ` up to ${max}` : ''}.`);
      return;
    }
    onChange(time);
    close();
  }

  function select(number: number) {
    setDraft(mode === 'hour'
      ? `${pad(number % 12 + (hour >= 12 ? 12 : 0))}:${pad(minute)}`
      : `${pad(hour)}:${pad(number * 5)}`);
    setMessage('');
    if (mode === 'hour') {
      setMode('minute');
      minuteRef.current?.focus({ preventScroll: true });
    }
  }

  useLayoutEffect(() => {
    if (!isOpen) return;
    const update = () => {
      const anchor = triggerRef.current?.getBoundingClientRect();
      if (!anchor) return;
      const viewport = window.visualViewport;
      const left = viewport?.offsetLeft ?? 0;
      const top = viewport?.offsetTop ?? 0;
      const width = viewport?.width ?? document.documentElement.clientWidth;
      const height = viewport?.height ?? window.innerHeight;
      const popupWidth = Math.min(304, width - 24);
      const maxHeight = Math.max(0, height - 24);
      const popupHeight = Math.min(popupRef.current?.scrollHeight ?? 480, maxHeight);
      const below = anchor.bottom + 6;
      const above = anchor.top - popupHeight - 6;
      setBounds({
        left: Math.max(left + 12, Math.min(anchor.left, left + width - popupWidth - 12)),
        top: below + popupHeight <= top + height - 12 ? below
          : above >= top + 12 ? above : top + Math.max(12, (height - popupHeight) / 2),
        width: popupWidth,
        maxHeight,
      });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    window.visualViewport?.addEventListener('resize', update);
    window.visualViewport?.addEventListener('scroll', update);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
      window.visualViewport?.removeEventListener('resize', update);
      window.visualViewport?.removeEventListener('scroll', update);
    };
  }, [isOpen, message]);

  useEffect(() => {
    if (!isOpen) return;
    hourRef.current?.focus({ preventScroll: true });
    const outside = (event: PointerEvent) => {
      if (!popupRef.current?.contains(event.target as Node) && !triggerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        setIsOpen(false);
        triggerRef.current?.focus({ preventScroll: true });
      }
      if (event.key === 'Tab') {
        const items = popupRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled)');
        if (!items?.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    };
    document.addEventListener('pointerdown', outside);
    window.addEventListener('keydown', keydown, true);
    return () => {
      document.removeEventListener('pointerdown', outside);
      window.removeEventListener('keydown', keydown, true);
    };
  }, [isOpen]);

  return (
    <div className={`min-w-0 w-full ${className}`}>
      <button
        ref={triggerRef} id={id} type="button" disabled={disabled}
        aria-label={`${label}: ${value.slice(0, 5) || placeholder}`}
        aria-haspopup="dialog" aria-expanded={isOpen} aria-controls={isOpen ? popupId : undefined}
        aria-describedby={error ? `${popupId}-field-error` : undefined}
        onClick={() => {
          if (isOpen) { close(); return; }
          setDraft(isTime(value.slice(0, 5)) ? value.slice(0, 5) : '09:00');
          setMode('hour'); setMessage(''); setIsOpen(true);
        }}
        className={`${control} flex w-full min-w-0 items-center justify-between gap-2 bg-[var(--bg-input)] py-2 text-sm text-[var(--text-primary)] disabled:opacity-50 ${error ? '!border-rose-500' : ''}`}
      >
        <span className={value ? 'font-mono font-medium' : 'text-[var(--text-muted)]'}>{value.slice(0, 5) || placeholder}</span>
        <span className="flex shrink-0 items-center gap-1.5 text-[var(--text-muted)]">
          <ClockIcon className="h-5 w-5" aria-hidden="true" />
          <ChevronDownIcon className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
      </button>
      {error && <span id={`${popupId}-field-error`} className="sr-only">Please choose a valid time.</span>}
      {name && <input type="hidden" name={name} value={value} disabled={disabled} />}
      {isOpen && createPortal(
        <div ref={popupRef} id={popupId} role="dialog" aria-label={`${label} clock picker`}
          className="fixed z-[150] overflow-y-auto overscroll-contain rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] p-4 text-[var(--text-primary)] shadow-2xl"
          style={bounds}
          onClick={(event) => event.stopPropagation()}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2 text-sm font-semibold"><ClockIcon className="h-5 w-5" aria-hidden="true" />{label}</span>
            <button type="button" aria-label="Close time picker" onClick={close} className={`${control} !px-2`}><XMarkIcon className="h-5 w-5" aria-hidden="true" /></button>
          </div>
          <div className="mt-2 flex items-center justify-center gap-2">
            <button ref={hourRef} type="button" aria-label="Select hour" aria-pressed={mode === 'hour'} onClick={() => setMode('hour')} className={`${control} font-mono text-2xl ${mode === 'hour' ? active : ''}`}>{pad(hour12)}</button>
            <span aria-hidden="true">:</span>
            <button ref={minuteRef} type="button" aria-label="Select minute" aria-pressed={mode === 'minute'} onClick={() => setMode('minute')} className={`${control} font-mono text-2xl ${mode === 'minute' ? active : ''}`}>{pad(minute)}</button>
            <div className="flex flex-col gap-1">
              {['AM', 'PM'].map((period, index) => <button key={period} type="button" aria-pressed={Math.floor(hour / 12) === index} onClick={() => { setDraft(`${pad(hour % 12 + index * 12)}:${pad(minute)}`); setMessage(''); }} className={`min-h-11 rounded-md px-3 py-1 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-[var(--brand-accent)] ${Math.floor(hour / 12) === index ? active : 'bg-[var(--bg-input)]'}`}>{period}</button>)}
            </div>
          </div>
          <p className="my-2 text-center text-xs text-[var(--text-muted)]" aria-live="polite">Choose {mode === 'hour' ? 'an hour' : 'minutes'}</p>
          <div role="group" aria-label={mode === 'hour' ? 'Hours' : 'Minutes'} className="relative mx-auto h-60 w-60 max-w-full rounded-full bg-[var(--bg-input)]">
            <div aria-hidden="true" className="absolute left-1/2 top-1/2 h-0.5 w-[38%] origin-left bg-[var(--brand-accent)]" style={{ transform: `rotate(${selected * 30 - 90}deg)` }} />
            <div aria-hidden="true" className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--brand-accent)]" />
            {Array.from({ length: 12 }, (_, index) => {
              const angle = index * Math.PI / 6;
              const number = mode === 'hour' ? index || 12 : index * 5;
              return <button key={`${mode}-${index}`} type="button" aria-label={`${mode === 'hour' ? 'Hour' : 'Minute'} ${number}`} aria-pressed={selected === index}
                onClick={() => select(index)}
                className={`absolute flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--brand-accent)] ${selected === index ? active : 'hover:bg-[var(--bg-card)]'}`}
                style={{ left: `${50 + Math.sin(angle) * 39}%`, top: `${50 - Math.cos(angle) * 39}%` }}
              >{mode === 'minute' ? pad(number) : number}</button>;
            })}
          </div>
          <label className="mt-3 block text-xs text-[var(--text-secondary)]">
            Exact time (24-hour HH:MM)
            <input type="text" value={draft} maxLength={5} placeholder="09:00" aria-invalid={!!message} aria-describedby={message ? `${popupId}-error` : undefined}
              onChange={(event) => { setDraft(event.target.value); setMessage(''); }}
              onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); apply(); } }}
              className={`${control} mt-1 w-full min-w-0 bg-[var(--bg-input)] font-mono text-base text-[var(--text-primary)]`}
            />
          </label>
          {message && <p id={`${popupId}-error`} role="alert" className="mt-2 text-xs text-rose-500">{message}</p>}
          <div className="mt-3 flex items-center justify-between gap-2">
            <button type="button" onClick={() => { onChange(''); close(); }} className={`${control} text-sm`}>Clear time</button>
            <button type="button" onClick={apply} className={`${control} ${active} text-sm font-semibold`}>Set time</button>
          </div>
        </div>, document.body,
      )}
    </div>
  );
}
