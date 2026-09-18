'use client';

import React, { Suspense } from 'react';
import { SettingsContent } from '@/app/settings/page';

export default function StudentSettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-20 text-[var(--text-muted)] text-sm">
          Loading Settings...
        </div>
      }
    >
      <SettingsContent showNavbar={false} />
    </Suspense>
  );
}
