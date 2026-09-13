'use client';

import React, { useState, useRef, useEffect } from 'react';

export interface TimePickerProps {
  value?: string; // "HH:MM"
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
  id?: string;
  name?: string;
  min?: string;
  max?: string;
}

// Quick-select slots in 30-minute increments from 00:00 to 23:30
const ALL_SLOTS: string[] = [];
for (let h = 0; h < 24; h++) {
  const hh = String(h).padStart(2, '0');
  ALL_SLOTS.push(`${hh}:00`);
  ALL_SLOTS.push(`${hh}:30`);
}

// Daytime primary range: 08:00 to 22:30 as specified
const DAYTIME_SLOTS = ALL_SLOTS.filter((time) => {
  const h = parseInt(time.split(':')[0], 10);
  return h >= 8 && (h < 22 || (h === 22 && time.endsWith(':30')));
});

export default function TimePicker({
  value = '',
  onChange,
  placeholder = 'Select time',
  disabled = false,
  error = false,
  className = '',
  id,
}: TimePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'daytime' | 'all'>('daytime');
  const [customTime, setCustomTime] = useState(value || '');
  const [customError, setCustomError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const [prevValue, setPrevValue] = useState(value);
  if (value !== prevValue) {
    setPrevValue(value);
    setCustomTime(value || '');
  }

  // Handle outside click & escape key
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

  // Scroll active item into view when opening
  useEffect(() => {
    if (isOpen && value) {
      const timer = setTimeout(() => {
        const activeBtn = dropdownRef.current?.querySelector(
          `[data-time="${value}"]`
        );
        if (activeBtn) {
          activeBtn.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen, value]);

  const handleSelectSlot = (slot: string) => {
    onChange(slot);
    setCustomTime(slot);
    setCustomError(null);
    setIsOpen(false);
  };

  const handleCustomApply = () => {
    const trimmed = customTime.trim();
    // Validate HH:MM (24-hour format)
    const match = trimmed.match(/^([01]\d|2[0-3]):([0-5]\d)$/);
    if (!match) {
      setCustomError('Use HH:MM (00:00 - 23:59)');
      return;
    }
    setCustomError(null);
    onChange(trimmed);
    setIsOpen(false);
  };

  const displayedTime = value ? value.slice(0, 5) : '';

  const slotsToDisplay = activeTab === 'daytime' ? DAYTIME_SLOTS : ALL_SLOTS;

  return (
    <div ref={containerRef} className={`relative inline-block w-full ${className}`}>
      {/* Trigger Button: Opens visual picker on click, never software keyboard */}
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
        <span className={displayedTime ? 'text-[var(--text-primary)] font-mono font-medium' : 'text-[var(--text-muted)]'}>
          {displayedTime || placeholder}
        </span>
        <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <svg
            className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform ${isOpen ? 'rotate-180 text-blue-500' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Hidden native time input for mobile touch fallback if triggered programmatically */}
      <input
        type="time"
        tabIndex={-1}
        aria-hidden="true"
        value={value ? value.slice(0, 5) : ''}
        onChange={(e) => onChange(e.target.value)}
        className="sr-only pointer-events-none"
      />

      {/* Dropdown Popup */}
      {isOpen && (
        <div
          ref={dropdownRef}
          role="dialog"
          aria-label="Time picker popup"
          className="
            absolute z-50 mt-1.5 left-0 right-0 sm:left-auto sm:right-auto sm:w-72
            bg-[var(--bg-card)] border border-[var(--border-color)] rounded-2xl shadow-2xl shadow-black/30
            p-3.5 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-150 backdrop-blur-md
          "
          style={{ minWidth: '280px' }}
        >
          {/* Header with Custom Manual Typing */}
          <div className="mb-3 pb-2.5 border-b border-[var(--border-color)]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-[var(--text-secondary)]">Custom Time</span>
              <span className="text-[10px] text-[var(--text-muted)]">24-hour format (HH:MM)</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                maxLength={5}
                placeholder="09:00"
                value={customTime}
                onChange={(e) => {
                  setCustomTime(e.target.value);
                  setCustomError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleCustomApply();
                  }
                }}
                className="
                  flex-1 px-3 py-1.5 bg-[var(--bg-input)] border border-[var(--border-color)] rounded-lg
                  text-sm font-mono text-[var(--text-primary)] placeholder-[var(--text-muted)]
                  focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40
                "
              />
              <button
                type="button"
                onClick={handleCustomApply}
                className="
                  px-3 py-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700
                  text-xs font-semibold text-white rounded-lg transition-colors cursor-pointer min-h-[36px]
                "
              >
                Set
              </button>
            </div>
            {customError && (
              <p className="text-[11px] text-rose-500 dark:text-rose-400 mt-1">{customError}</p>
            )}
          </div>

          {/* Tab Selector: Daytime (08:00 - 22:30) vs 24 Hours */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex rounded-lg bg-[var(--bg-secondary)] p-0.5 border border-[var(--border-color)] text-[11px] font-medium">
              <button
                type="button"
                onClick={() => setActiveTab('daytime')}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  activeTab === 'daytime'
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-xs font-semibold'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                }`}
              >
                08:00 – 22:30
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('all')}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  activeTab === 'all'
                    ? 'bg-[var(--bg-card)] text-[var(--text-primary)] shadow-xs font-semibold'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                }`}
              >
                Full 24h
              </button>
            </div>
            <span className="text-[10px] text-[var(--text-muted)]">30 min step</span>
          </div>

          {/* Quick-Select Grid */}
          <div
            ref={listRef}
            className="grid grid-cols-3 sm:grid-cols-3 gap-1.5 max-h-56 overflow-y-auto pr-1 py-1"
          >
            {slotsToDisplay.map((slot) => {
              const isSelected = value?.slice(0, 5) === slot;
              return (
                <button
                  key={slot}
                  type="button"
                  data-time={slot}
                  onClick={() => handleSelectSlot(slot)}
                  className={`
                    px-2 py-2 min-h-[44px] sm:min-h-[38px] rounded-lg text-xs font-mono font-medium transition-all
                    flex items-center justify-center cursor-pointer select-none
                    ${
                      isSelected
                        ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-600/30 scale-[1.02]'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border-color)] hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]'
                    }
                  `}
                >
                  {slot}
                </button>
              );
            })}
          </div>

          {/* Mobile Native Option / Clear */}
          <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => {
                onChange('');
                setIsOpen(false);
              }}
              className="text-[11px] text-[var(--text-muted)] hover:text-rose-500 transition-colors cursor-pointer"
            >
              Clear time
            </button>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
