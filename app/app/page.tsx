'use client';

import React from 'react';
import LandingNavbar from '@/components/landing/LandingNavbar';
import HeroSection from '@/components/landing/HeroSection';
import ProblemSection from '@/components/landing/ProblemSection';
import SolutionSection from '@/components/landing/SolutionSection';
import FeaturesSection from '@/components/landing/FeaturesSection';
import DemoSection from '@/components/landing/DemoSection';
import StatsAndTestimonials from '@/components/landing/StatsAndTestimonials';
import EuropeSection from '@/components/landing/EuropeSection';
import CtaSection from '@/components/landing/CtaSection';
import LandingFooter from '@/components/landing/LandingFooter';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex flex-col selection:bg-indigo-500/30 selection:text-white">
      {/* Sticky Top Navbar */}
      <LandingNavbar />

      {/* Main Single Long Scrolling Page */}
      <main className="flex-1 w-full">
        {/* 1. Hero Section (100vh) */}
        <HeroSection />

        {/* 2. Problem Section */}
        <ProblemSection />

        {/* 3. Solution Section */}
        <SolutionSection />

        {/* 4. Features Section */}
        <FeaturesSection />

        {/* 5. Live Demo Section */}
        <DemoSection />

        {/* 6. Testimonials & Stats Section */}
        <StatsAndTestimonials />

        {/* 7. How It Helps (Europe & Germany Section) */}
        <EuropeSection />

        {/* 8. Bottom CTA Banner */}
        <CtaSection />
      </main>

      {/* 9. Footer */}
      <LandingFooter />
    </div>
  );
}
