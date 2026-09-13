'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';
import { useThemeContext } from '@/context/ThemeContext';

export default function LandingNavbar() {
  const router = useRouter();
  const { resolvedTheme, toggleTheme } = useThemeContext();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[var(--navbar-bg)] backdrop-blur-md border-b border-[var(--border-color)] shadow-xl py-3'
          : 'bg-transparent py-4 sm:py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/"
          className="flex items-center gap-2.5 text-[var(--text-primary)] font-black text-lg sm:text-xl tracking-tight hover:opacity-90 transition group"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
            <span className="text-base">⚡</span>
          </div>
          <span className="bg-gradient-to-r from-[var(--text-primary)] via-[var(--text-secondary)] to-indigo-500 bg-clip-text text-transparent">
            SyncShift
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-[var(--text-secondary)]">
          <button
            onClick={() => scrollToSection('how-it-works')}
            className="hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            How It Works
          </button>
          <button
            onClick={() => scrollToSection('features')}
            className="hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            Features
          </button>
          <button
            onClick={() => scrollToSection('demo')}
            className="hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            Live Demo
          </button>
          <button
            onClick={() => scrollToSection('europe')}
            className="hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            Europe & Visa
          </button>
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3">
          {/* Quick theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] transition cursor-pointer shadow-xs"
            aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={resolvedTheme === 'dark' ? 'Switch to light mode (☀️)' : 'Switch to dark mode (🌙)'}
          >
            <span className="text-sm select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
          </button>

          <Link
            href="/login"
            className="px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-lg shadow-indigo-600/25 hover:scale-[1.02] active:scale-[0.98]"
          >
            Get Started Free →
          </Link>
        </div>

        {/* Mobile Actions: Toggle & Hamburger */}
        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
            aria-label="Toggle light/dark theme"
            title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <span className="text-sm select-none">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
          </button>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? <XMarkIcon className="w-5 h-5" /> : <Bars3Icon className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[var(--bg-card)] border-b border-[var(--border-color)] px-4 py-5 space-y-3 backdrop-blur-xl animate-fade-in text-[var(--text-primary)] shadow-2xl">
          <button
            onClick={() => scrollToSection('how-it-works')}
            className="w-full text-left py-2 text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            How It Works
          </button>
          <button
            onClick={() => scrollToSection('features')}
            className="w-full text-left py-2 text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            Features
          </button>
          <button
            onClick={() => scrollToSection('demo')}
            className="w-full text-left py-2 text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            Live Demo
          </button>
          <button
            onClick={() => scrollToSection('europe')}
            className="w-full text-left py-2 text-sm font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            Europe & Visa
          </button>
          <div className="pt-3 border-t border-[var(--border-color)] flex flex-col gap-2.5">
            <Link
              href="/login"
              className="w-full py-2.5 text-center text-xs font-semibold text-[var(--text-primary)] bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)]"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="w-full py-2.5 text-center text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-md"
            >
              Get Started Free →
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
