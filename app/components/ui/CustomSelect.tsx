'use client';

import React, { useState, useRef, useEffect, useMemo, useId } from 'react';
import { ChevronDownIcon, CheckIcon, MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/20/solid';

export interface SelectOption {
  value: string | number;
  label: string;
  sublabel?: string;
  group?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface CustomSelectProps {
  options: SelectOption[];
  value: string | number | undefined | null;
  onChange: (value: any) => void;
  placeholder?: string;
  searchable?: boolean;
  disabled?: boolean;
  className?: string;
  id?: string;
  name?: string;
  required?: boolean;
  size?: 'sm' | 'md';
  label?: string | React.ReactNode;
  error?: string;
  helperText?: string;
  loading?: boolean;
  portalTheme?: 'default' | 'student' | 'university';
}

export default function CustomSelect({
  options,
  value,
  onChange,
  placeholder = 'Select option...',
  searchable = false,
  disabled = false,
  className = '',
  id,
  name,
  required = false,
  size = 'md',
  label,
  error,
  helperText,
  loading = false,
  portalTheme = 'default',
}: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const [dropUp, setDropUp] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const optionsListRef = useRef<HTMLDivElement>(null);

  const autoId = useId();
  const selectId = id || autoId;
  const helperId = `${selectId}-helper`;
  const errorId = `${selectId}-error`;

  // Currently selected option
  const selectedOption = useMemo(() => {
    return options.find((opt) => String(opt.value) === String(value));
  }, [options, value]);

  // Filtered options based on search query
  const filteredOptions = useMemo(() => {
    if (!searchable || !searchQuery.trim()) return options;
    const query = searchQuery.toLowerCase().trim();
    return options.filter((opt) => {
      const matchLabel = opt.label.toLowerCase().includes(query);
      const matchValue = String(opt.value).toLowerCase().includes(query);
      const matchSub = opt.sublabel?.toLowerCase().includes(query) ?? false;
      const matchGroup = opt.group?.toLowerCase().includes(query) ?? false;
      return matchLabel || matchValue || matchSub || matchGroup;
    });
  }, [options, searchable, searchQuery]);

  // Grouped options map
  const groupedOptions = useMemo(() => {
    const hasGroups = filteredOptions.some((opt) => Boolean(opt.group));
    if (!hasGroups) return null;

    const groups: { [key: string]: SelectOption[] } = {};
    for (const opt of filteredOptions) {
      const g = opt.group || 'Other';
      if (!groups[g]) groups[g] = [];
      groups[g].push(opt);
    }
    return groups;
  }, [filteredOptions]);

  // Handle open / close position (check if dropdown should open above or below)
  const openDropdown = () => {
    if (disabled || loading) return;

    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      // If less than 280px below and more space above, drop up
      setDropUp(spaceBelow < 280 && spaceAbove > spaceBelow);
    }

    setIsOpen(true);
    setSearchQuery('');
    const curIdx = filteredOptions.findIndex((opt) => String(opt.value) === String(value));
    setHighlightedIndex(curIdx >= 0 ? curIdx : 0);
  };

  const closeDropdown = () => {
    setIsOpen(false);
    setSearchQuery('');
    setHighlightedIndex(-1);
  };

  // Close when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        closeDropdown();
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
    };
  }, [isOpen]);

  // Auto-focus search input when opened
  useEffect(() => {
    if (isOpen && searchable) {
      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen, searchable]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && highlightedIndex >= 0 && optionsListRef.current) {
      const highlightedEl = optionsListRef.current.querySelector(
        `[data-option-index="${highlightedIndex}"]`
      ) as HTMLElement | null;
      if (highlightedEl) {
        highlightedEl.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, isOpen]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled || loading) return;

    if (!isOpen) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
        e.preventDefault();
        openDropdown();
      }
      return;
    }

    if (e.key === 'Escape' || e.key === 'Tab') {
      closeDropdown();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        let next = prev + 1;
        while (next < filteredOptions.length && filteredOptions[next]?.disabled) {
          next++;
        }
        return next < filteredOptions.length ? next : prev;
      });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => {
        let next = prev - 1;
        while (next >= 0 && filteredOptions[next]?.disabled) {
          next--;
        }
        return next >= 0 ? next : prev;
      });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (
        highlightedIndex >= 0 &&
        highlightedIndex < filteredOptions.length &&
        !filteredOptions[highlightedIndex]?.disabled
      ) {
        handleSelect(filteredOptions[highlightedIndex].value);
      }
    }
  };

  const handleSelect = (val: string | number) => {
    onChange(val);
    closeDropdown();
  };

  const isUniversity = portalTheme === 'university';
  const accentBorder = isUniversity ? 'border-emerald-500 ring-2 ring-emerald-500/25' : 'border-indigo-500 ring-2 ring-indigo-500/25';
  const accentChevron = isUniversity ? 'text-emerald-500' : 'text-indigo-500';
  const minHeightClass = size === 'sm' ? 'min-h-[38px] py-1.5 px-3 text-xs' : 'min-h-[44px] py-2.5 px-3.5 text-xs sm:text-sm';

  return (
    <div className={`w-full ${className}`}>
      {/* Optional Top Label */}
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5"
        >
          {label}
          {required && <span className="text-red-400 ml-1">*</span>}
        </label>
      )}

      <div
        ref={containerRef}
        className="relative w-full"
        onKeyDown={handleKeyDown}
      >
        {/* Hidden input for standard form submission */}
        {name && (
          <input
            type="hidden"
            name={name}
            value={value ?? ''}
            required={required}
          />
        )}

        {/* Trigger Button */}
        <button
          id={selectId}
          type="button"
          disabled={disabled || loading}
          onClick={() => (isOpen ? closeDropdown() : openDropdown())}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : helperText ? helperId : undefined}
          className={`w-full flex items-center justify-between gap-2.5 rounded-xl text-left bg-[var(--bg-card)] border transition-all duration-150 select-none cursor-pointer focus:outline-none ${minHeightClass} ${
            disabled
              ? 'opacity-50 cursor-not-allowed bg-[var(--bg-input)] border-[var(--border-color)] text-[var(--text-muted)]'
              : error
              ? 'border-red-500 ring-1 ring-red-500/30 bg-[var(--bg-card)] text-[var(--text-primary)]'
              : isOpen
              ? `${accentBorder} bg-[var(--bg-secondary)]`
              : 'border-[var(--border-color)] hover:border-[var(--border-hover)] text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
          }`}
        >
          <div className="flex items-center gap-2 truncate min-w-0">
            {selectedOption?.icon && (
              <span className="shrink-0">{selectedOption.icon}</span>
            )}
            {loading ? (
              <div className="flex items-center gap-2 text-[var(--text-muted)]">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Loading...</span>
              </div>
            ) : selectedOption ? (
              <span className="truncate text-[var(--text-primary)] font-normal">
                {selectedOption.label}
              </span>
            ) : (
              <span className="truncate text-[var(--text-muted)]">{placeholder}</span>
            )}
          </div>

          <ChevronDownIcon
            className={`w-4 h-4 text-[var(--text-muted)] shrink-0 transition-transform duration-200 ${
              isOpen ? `rotate-180 ${accentChevron}` : ''
            }`}
          />
        </button>

        {/* Dropdown Panel */}
        {isOpen && (
          <div
            ref={panelRef}
            className={`absolute left-0 right-0 z-[1000] w-full rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] shadow-2xl overflow-hidden animate-fade-in flex flex-col text-[var(--text-primary)] ${
              dropUp ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
            }`}
            style={{ maxHeight: '280px' }}
          >
            {/* Search Input if searchable */}
            {searchable && (
              <div className="p-2 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] shrink-0">
                <div className="relative flex items-center">
                  <MagnifyingGlassIcon className="w-4 h-4 text-[var(--text-muted)] absolute left-2.5 pointer-events-none" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search options..."
                    className={`w-full pl-8 pr-7 py-1.5 rounded-lg bg-[var(--bg-input)] border border-[var(--border-color)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none transition ${
                      isUniversity
                        ? 'focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50'
                        : 'focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50'
                    }`}
                    onKeyDown={(e) => {
                      e.stopPropagation();
                    }}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] p-0.5 cursor-pointer"
                    >
                      <XMarkIcon className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Options List */}
            <div
              ref={optionsListRef}
              className="overflow-y-auto flex-1 py-1 divide-y divide-[var(--border-color)] custom-theme-scrollbar"
              role="listbox"
            >
              {filteredOptions.length === 0 ? (
                <div className="px-4 py-6 text-center text-xs text-[var(--text-muted)] italic">
                  No matching options found
                </div>
              ) : groupedOptions ? (
                // Grouped Options Rendering
                Object.entries(groupedOptions).map(([groupName, groupItems]) => (
                  <div key={groupName} className="py-1">
                    <div className="px-3.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] bg-[var(--bg-secondary)] sticky top-0 z-10 backdrop-blur-xs">
                      {groupName}
                    </div>
                    {groupItems.map((opt) => {
                      const optIdx = filteredOptions.indexOf(opt);
                      const isSelected = String(opt.value) === String(value);
                      const isHighlighted = optIdx === highlightedIndex;

                      return (
                        <OptionItem
                          key={String(opt.value)}
                          option={opt}
                          index={optIdx}
                          isSelected={isSelected}
                          isHighlighted={isHighlighted}
                          isUniversity={isUniversity}
                          onSelect={() => handleSelect(opt.value)}
                          onHover={() => setHighlightedIndex(optIdx)}
                        />
                      );
                    })}
                  </div>
                ))
              ) : (
                // Flat Options Rendering
                filteredOptions.map((opt, idx) => {
                  const isSelected = String(opt.value) === String(value);
                  const isHighlighted = idx === highlightedIndex;

                  return (
                    <OptionItem
                      key={String(opt.value)}
                      option={opt}
                      index={idx}
                      isSelected={isSelected}
                      isHighlighted={isHighlighted}
                      isUniversity={isUniversity}
                      onSelect={() => handleSelect(opt.value)}
                      onHover={() => setHighlightedIndex(idx)}
                    />
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Error / Helper text */}
      {error ? (
        <p id={errorId} className="text-xs text-red-500 mt-1">
          {error}
        </p>
      ) : helperText ? (
        <p id={helperId} className="text-xs text-[var(--text-muted)] mt-1">
          {helperText}
        </p>
      ) : null}
    </div>
  );
}

// Single option item component
function OptionItem({
  option,
  index,
  isSelected,
  isHighlighted,
  isUniversity,
  onSelect,
  onHover,
}: {
  option: SelectOption;
  index: number;
  isSelected: boolean;
  isHighlighted: boolean;
  isUniversity: boolean;
  onSelect: () => void;
  onHover: () => void;
}) {
  const selectedStyle = isUniversity
    ? 'bg-emerald-500/15 border-l-[3px] border-emerald-500 text-[var(--text-primary)] font-medium pl-[11px]'
    : 'bg-indigo-600/15 border-l-[3px] border-indigo-500 text-[var(--text-primary)] font-medium pl-[11px]';

  const checkColor = isUniversity ? 'text-emerald-500' : 'text-indigo-500';

  return (
    <div
      data-option-index={index}
      role="option"
      aria-selected={isSelected}
      onClick={option.disabled ? undefined : onSelect}
      onMouseEnter={onHover}
      className={`px-3.5 py-2.5 text-xs sm:text-sm flex items-center justify-between gap-3 cursor-pointer transition-colors duration-100 ${
        option.disabled
          ? 'opacity-40 cursor-not-allowed text-[var(--text-muted)]'
          : isSelected
          ? selectedStyle
          : isHighlighted
          ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] border-l-[3px] border-transparent pl-[11px]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] border-l-[3px] border-transparent pl-[11px]'
      }`}
    >
      <div className="flex items-center gap-2.5 truncate min-w-0">
        {option.icon && <span className="shrink-0">{option.icon}</span>}
        <div className="truncate">
          <div className="truncate leading-snug">{option.label}</div>
          {option.sublabel && (
            <div className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
              {option.sublabel}
            </div>
          )}
        </div>
      </div>

      {isSelected && (
        <CheckIcon className={`w-4 h-4 shrink-0 ${checkColor}`} />
      )}
    </div>
  );
}
