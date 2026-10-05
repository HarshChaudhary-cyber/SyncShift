import type { Metadata } from 'next';
import LandingExperience from '@/components/landing/LandingExperience';

export const metadata: Metadata = {
  title: 'SyncShift — Your university day, in sync.',
  description: 'One workspace for university schedules, teaching, and personal plans. Connected experiences for students, professors, and university administration.',
};

export default function LandingPage() {
  return <LandingExperience />;
}
