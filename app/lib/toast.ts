/**
 * Lightweight, zero-dependency toast notification system.
 * Renders animated, dark-mode compatible floating toast alerts.
 */

export type ToastType = 'error' | 'success' | 'info';

export function showToast(message: string, type: ToastType = 'info', durationMs = 4000): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  // Locate or create container
  let container = document.getElementById('syncshift-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'syncshift-toast-container';
    container.className =
      'fixed top-5 right-5 z-[9999] flex flex-col gap-2.5 max-w-sm pointer-events-none';
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement('div');
  toast.setAttribute('role', 'alert');
  toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl text-xs sm:text-sm font-medium transition-all duration-300 transform -translate-y-2 opacity-0 ${
    type === 'error'
      ? 'bg-rose-950/95 text-rose-100 border-rose-600 shadow-rose-950/50 backdrop-blur-md'
      : type === 'success'
      ? 'bg-emerald-950/95 text-emerald-100 border-emerald-600 shadow-emerald-950/50 backdrop-blur-md'
      : 'bg-zinc-900/95 text-zinc-100 border-zinc-700 shadow-black/50 backdrop-blur-md'
  }`;

  const icon = type === 'error' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️';

  const iconSpan = document.createElement('span');
  iconSpan.className = 'text-base shrink-0';
  iconSpan.textContent = icon;

  const msgSpan = document.createElement('span');
  msgSpan.className = 'flex-1 leading-snug';
  msgSpan.textContent = message;

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'ml-2 text-xs opacity-60 hover:opacity-100 transition-opacity p-1 cursor-pointer';
  closeBtn.setAttribute('aria-label', 'Close toast');
  closeBtn.textContent = '✕';

  toast.appendChild(iconSpan);
  toast.appendChild(msgSpan);
  toast.appendChild(closeBtn);

  container.appendChild(toast);

  // Trigger smooth enter transition
  requestAnimationFrame(() => {
    toast.classList.remove('-translate-y-2', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');
  });

  const dismiss = () => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('-translate-y-2', 'opacity-0');
    setTimeout(() => {
      toast.remove();
      if (container && container.childNodes.length === 0) {
        container.remove();
      }
    }, 300);
  };

  closeBtn.addEventListener('click', dismiss);
  setTimeout(dismiss, durationMs);
}

export const showErrorToast = (msg: string): void => showToast(msg, 'error', 4500);
export const showSuccessToast = (msg: string): void => showToast(msg, 'success', 3000);
export const showInfoToast = (msg: string): void => showToast(msg, 'info', 3500);
