'use client';

import { useEffect } from 'react';

/** Keep overlays in the visible area when the software keyboard opens or pans it. */
export default function ViewportMetrics() {
  useEffect(() => {
    const viewport = window.visualViewport;
    const update = () => {
      document.documentElement.style.setProperty('--visible-viewport-height', `${viewport?.height ?? window.innerHeight}px`);
      document.documentElement.style.setProperty('--visible-viewport-top', `${viewport?.offsetTop ?? 0}px`);
    };
    update();
    window.addEventListener('resize', update);
    viewport?.addEventListener('resize', update);
    viewport?.addEventListener('scroll', update);
    return () => {
      window.removeEventListener('resize', update);
      viewport?.removeEventListener('resize', update);
      viewport?.removeEventListener('scroll', update);
      document.documentElement.style.removeProperty('--visible-viewport-height');
      document.documentElement.style.removeProperty('--visible-viewport-top');
    };
  }, []);
  return null;
}
