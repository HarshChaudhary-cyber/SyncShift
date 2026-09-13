'use client';

import React, { useState, useEffect } from 'react';

export interface ClientOnlyDndProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * ClientOnlyDnd prevents drag-and-drop hydration mismatches by ensuring that
 * dnd-kit components (which dynamically inject aria-disabled, aria-pressed,
 * and aria-roledescription="draggable") only render after mounting on the client.
 */
export default function ClientOnlyDnd({
  children,
  fallback = null,
}: ClientOnlyDndProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
