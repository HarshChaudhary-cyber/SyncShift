'use client';

import React, { useState, useRef, useEffect } from 'react';
import { format } from 'date-fns';

export interface DatePickerProps {
  value: string | null; // "YYYY-MM-DD" or null
  onChange: (value: string | null) => void;
  nullable?: boolean;
  minDate?: string | null; // "YYYY-MM-DD"
  maxDate?: string | null; // "YYYY-MM-DD"
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
  id?: string;
  name?: string;
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function DatePicker({
  value,
  onChange,
  nullable = false,
  minDate = null,
  maxDate = null,
  placeholder = 'Select date',
  disabled = false,
  error = false,
  className = '',
  id,
}: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Default view date to currently selected value, or minDate, or today
  const getInitialViewDate = () => {
    if (value) {
      try {
        return parseLocalDate(value);
      } catch {
        // fallback
      }
    }
    if (minDate) {
      try {
        return parseLocalDate(minDate);
      } catch {
        // fallback
      }
    }
    return new Date();
  };

  const [viewDate, setViewDate] = useState<Date>(getInitialViewDate);

  const containerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const [prevValue, setPrevValue] = useState(value);
  if (value !== prevValue) {
    setPrevValue(value);
    if (value) {
      try {
        setViewDate(parseLocalDate(value));
      } catch {
        // ignore
      }
    }
  }

  // Outside click & Escape listener
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  // Month navigation
  const prevMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
  };

  // Calendar calculations
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth(); // 0-indexed
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7; // Monday = 0, Sunday = 6

  const todayStr = toDateString(new Date());

  // Format display string
  let displayString = '';
  if (value) {
    try {
      const d = parseLocalDate(value);
      displayString = format(d, 'EEE, d MMM yyyy');
    } catch {
      displayString = value;
    }
  } else if (nullable) {
    displayString = 'Ongoing / No end date';
  } else {
    displayString = placeholder;
  }

  const handleSelectDay = (dayNum: number) => {
    const selected = new Date(year, month, dayNum);
    const dateStr = toDateString(selected);

    // Guard against minDate / maxDate
    if (minDate && dateStr < minDate) return;
    if (maxDate && dateStr > maxDate) return;

    onChange(dateStr);
    setIsOpen(false);
  };

  const handleToggleOngoing = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      onChange(null);
      setIsOpen(false);
    } else {
      onChange(minDate || todayStr);
    }
  };

  return (
    <div ref={containerRef} className={`relative inline-block w-full ${className}`}>
      {/* Trigger Button: Visual picker opens on click, never software keyboard */}
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className={`
          w-full flex items-center justify-between gap-2 px-3 py-2 sm:py-2 min-h-[44px] sm:min-h-[38px]
          bg-[var(--bg-input)] border rounded-lg text-sm text-left transition-all select-none cursor-pointer
          ${disabled ? 'opacity-50 cursor-not-allowed bg-[var(--bg-secondary)]' : 'hover:border-[var(--border-hover)]'}
          ${
            error
              ? 'border-rose-500/80 focus:border-rose-500 focus:ring-1 focus:ring-rose-500/30'
              : isOpen
              ? 'border-blue-500 ring-1 ring-blue-500/30'
              : 'border-[var(--border-color)]'
          }
        `}
      >
        <span
          className={
            value
              ? 'text-[var(--text-primary)] font-medium'
              : nullable
              ? 'text-[var(--text-muted)] italic'
              : 'text-[var(--text-muted)]'
          }
        >
          {displayString}
        </span>
        <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <svg
            className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform ${isOpen ? 'rotate-180 text-blue-600 dark:text-blue-400' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Calendar Popup */}
      {isOpen && (
        <div
          ref={popupRef}
          role="dialog"
          aria-label="Date picker calendar"
          className="
            absolute z-50 mt-1.5 left-0 right-0 sm:left-auto sm:right-auto sm:w-80
            bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl shadow-2xl shadow-black/30
            p-4 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md
          "
          style={{ minWidth: '290px' }}
        >
          {/* Header Month / Year & Prev/Next Navigation */}
          <div className="flex items-center justify-between mb-3.5 pb-2 border-b border-[var(--border-color)]">
            <button
              type="button"
              onClick={prevMonth}
              className="p-2 min-w-[36px] min-h-[36px] rounded-lg hover:bg-[var(--bg-secondary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer flex items-center justify-center"
              aria-label="Previous month"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="text-sm font-semibold text-[var(--text-primary)] tracking-wide">
              {format(viewDate, 'MMMM yyyy')}
            </div>
            <button
              type="button"
              onClick={nextMonth}
              className="p-2 min-w-[36px] min-h-[36px] rounded-lg hover:bg-[var(--bg-secondary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer flex items-center justify-center"
              aria-label="Next month"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {/* Nullable "No end date" Option */}
          {nullable && (
            <div className="mb-3 p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl flex items-center justify-between">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs select-none">
                <input
                  type="checkbox"
                  checked={value === null}
                  onChange={handleToggleOngoing}
                  className="w-4 h-4 rounded text-blue-600 bg-[var(--bg-input)] border-[var(--border-color)] focus:ring-blue-500 cursor-pointer"
                />
                <span className={`font-medium ${value === null ? 'text-blue-600 dark:text-blue-400 font-semibold' : 'text-[var(--text-secondary)]'}`}>
                  Ongoing / No end date
                </span>
              </label>
              {value === null && (
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                  Active
                </span>
              )}
            </div>
          )}

          {/* Calendar Weekday Names */}
          <div className="grid grid-cols-7 gap-1 text-center mb-1 text-[11px] font-semibold text-[var(--text-muted)]">
            {WEEKDAYS.map((wd) => (
              <div key={wd} className="py-1">
                {wd}
              </div>
            ))}
          </div>

          {/* Day Grid */}
          <div className="grid grid-cols-7 gap-1 text-center">
            {/* Blank offset tiles */}
            {Array.from({ length: firstDayIndex }).map((_, i) => (
              <div key={`blank-${i}`} className="w-full aspect-square" />
            ))}

            {/* Days of Month */}
            {Array.from({ length: daysInMonth }).map((_, idx) => {
              const dayNum = idx + 1;
              const curDateStr = toDateString(new Date(year, month, dayNum));
              const isSelected = value === curDateStr;
              const isToday = curDateStr === todayStr;

              // Check if date is disabled due to minDate or maxDate
              const isBeforeMin = minDate ? curDateStr < minDate : false;
              const isAfterMax = maxDate ? curDateStr > maxDate : false;
              const isDisabled = isBeforeMin || isAfterMax;

              return (
                <button
                  key={dayNum}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => handleSelectDay(dayNum)}
                  className={`
                    w-full aspect-square min-w-[36px] min-h-[36px] sm:min-w-[32px] sm:min-h-[32px]
                    rounded-lg text-xs font-medium flex items-center justify-center transition-all select-none
                    ${
                      isDisabled
                        ? 'opacity-25 cursor-not-allowed text-[var(--text-muted)]'
                        : isSelected
                        ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-600/40 scale-105'
                        : 'text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] cursor-pointer'
                    }
                    ${isToday && !isSelected ? 'ring-1 ring-blue-500 font-bold text-blue-500 dark:text-blue-400' : ''}
                  `}
                  title={isDisabled ? (isBeforeMin ? 'Cannot be before start date' : 'Date not allowed') : undefined}
                >
                  <span className={isToday && !isSelected ? 'underline decoration-blue-500 underline-offset-2' : ''}>
                    {dayNum}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Quick Footer Action: Today & Close */}
          <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => {
                const today = new Date();
                const todayStrFormatted = toDateString(today);
                if (!minDate || todayStrFormatted >= minDate) {
                  onChange(todayStrFormatted);
                  setViewDate(today);
                  setIsOpen(false);
                } else {
                  setViewDate(today);
                }
              }}
              className="text-[11px] text-blue-500 dark:text-blue-400 hover:underline transition cursor-pointer font-medium"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
