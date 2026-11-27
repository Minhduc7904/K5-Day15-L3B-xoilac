'use client';

import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/cn';
import type { Tone } from './feedback';

interface ToastInput {
  title: string;
  description?: string;
  tone?: Tone;
  /** Mili giây; mặc định 4500. */
  duration?: number;
}

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: Tone;
}

const ToastContext = createContext<((toast: ToastInput) => void) | null>(null);

const icons = { info: Info, success: CircleCheck, warning: TriangleAlert, danger: CircleAlert };
const iconTones = { info: 'text-info', success: 'text-success', warning: 'text-warning', danger: 'text-danger' };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const show = useCallback(
    ({ tone = 'info', duration = 4500, title, description }: ToastInput) => {
      const id = ++nextId.current;
      setToasts((list) => [...list.slice(-2), { id, tone, title, description }]);
      window.setTimeout(() => dismiss(id), duration);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-[90] flex flex-col items-center gap-2 sm:inset-x-auto sm:right-6 sm:bottom-6 sm:items-end"
      >
        <AnimatePresence initial={false}>
          {toasts.map((toast) => {
            const Icon = icons[toast.tone];
            return (
              <motion.div
                key={toast.id}
                layout
                role={toast.tone === 'danger' ? 'alert' : 'status'}
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
                transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border border-border bg-background p-4 shadow-lift"
              >
                <Icon className={cn('mt-0.5 size-5 shrink-0', iconTones[toast.tone])} aria-hidden="true" />
                <div className="grid flex-1 gap-0.5">
                  <p className="text-label font-semibold text-foreground">{toast.title}</p>
                  {toast.description && <p className="text-caption text-muted-foreground">{toast.description}</p>}
                </div>
                <button
                  type="button"
                  aria-label="Đóng thông báo"
                  onClick={() => dismiss(toast.id)}
                  className="-m-1 inline-flex size-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <X className="size-4" aria-hidden="true" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const show = useContext(ToastContext);
  if (!show) throw new Error('useToast cần được gọi bên trong ToastProvider');
  return show;
}
