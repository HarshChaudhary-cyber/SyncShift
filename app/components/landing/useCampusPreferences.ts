'use client';
import { useSyncExternalStore } from 'react';

function subscribe(callback: () => void) {
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  media.addEventListener('change', callback);
  window.addEventListener('syncshift:reduced-motion-change', callback);
  return () => { media.removeEventListener('change', callback); window.removeEventListener('syncshift:reduced-motion-change', callback); };
}
function snapshot() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches || document.documentElement.dataset.reducedMotion === 'reduced';
}
export function useCampusReducedMotion() {
  return useSyncExternalStore(subscribe, snapshot, () => true);
}
