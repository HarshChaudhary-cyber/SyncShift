'use client';

import React from 'react';
import { CalendarProvider } from '@/context/CalendarContext';
import { PlannerContent } from '@/app/planner/page';

export default function StudentPlannerPage() {
  return (
    <CalendarProvider>
      <PlannerContent showNavbar={false} />
    </CalendarProvider>
  );
}
