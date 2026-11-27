'use client';

import { ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

/* ---------- Accordion ---------- */

export interface AccordionItem {
  id: string;
  title: ReactNode;
  content: ReactNode;
}

interface AccordionProps {
  items: AccordionItem[];
  defaultOpenId?: string;
  className?: string;
}

/** Mở một mục mỗi lần. Nút tiêu đề có aria-expanded, nội dung là region gắn với nút. */
export function Accordion({ items, defaultOpenId, className }: AccordionProps) {
  const [openId, setOpenId] = useState<string | undefined>(defaultOpenId);
  const baseId = useId();

  return (
    <div className={cn('grid gap-3', className)}>
      {items.map((item) => {
        const open = item.id === openId;
        const buttonId = `${baseId}-${item.id}-button`;
        const panelId = `${baseId}-${item.id}-panel`;
        return (
          <div
            key={item.id}
            className={cn(
              'rounded-2xl border bg-background transition-[border-color,box-shadow] duration-300',
              open ? 'border-primary/30 shadow-soft' : 'border-border hover:border-primary/20',
            )}
          >
            <h3>
              <button
                id={buttonId}
                type="button"
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpenId(open ? undefined : item.id)}
                className="flex w-full items-center justify-between gap-4 rounded-2xl px-5 py-4 text-left text-body font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:px-6"
              >
                {item.title}
                <motion.span
                  animate={{ rotate: open ? 180 : 0 }}
                  transition={{ duration: 0.25 }}
                  className={cn(
                    'flex size-8 shrink-0 items-center justify-center rounded-full transition-colors',
                    open ? 'bg-primary text-primary-foreground' : 'bg-surface-muted text-primary',
                  )}
                >
                  <ChevronDown className="size-4" aria-hidden="true" />
                </motion.span>
              </button>
            </h3>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-5 text-body text-muted-foreground sm:px-6">{item.content}</div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Tabs ---------- */

export interface TabItem {
  id: string;
  label: ReactNode;
  content: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  defaultId?: string;
  label: string;
  className?: string;
}

/** Tab theo mẫu WAI-ARIA: phím mũi tên, Home, End để chuyển tab. */
export function Tabs({ items, defaultId, label, className }: TabsProps) {
  const [active, setActive] = useState(defaultId ?? items[0]?.id);
  const baseId = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const last = items.length - 1;
    const next =
      event.key === 'ArrowRight' ? (index === last ? 0 : index + 1)
      : event.key === 'ArrowLeft' ? (index === 0 ? last : index - 1)
      : event.key === 'Home' ? 0
      : event.key === 'End' ? last
      : null;
    if (next === null) return;
    event.preventDefault();
    setActive(items[next].id);
    refs.current[next]?.focus();
  };

  const current = items.find((item) => item.id === active);

  return (
    <div className={cn('grid gap-4', className)}>
      <div role="tablist" aria-label={label} className="inline-flex w-fit max-w-full gap-1 overflow-x-auto rounded-2xl bg-surface-muted p-1">
        {items.map((item, index) => {
          const selected = item.id === active;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[index] = el;
              }}
              id={`${baseId}-${item.id}-tab`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${baseId}-${item.id}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(item.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
              className={cn(
                'relative shrink-0 rounded-xl px-4 py-2 text-label transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                selected ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {selected && (
                <motion.span
                  layoutId={`${baseId}-pill`}
                  transition={{ type: 'spring', stiffness: 500, damping: 38 }}
                  className="absolute inset-0 rounded-xl bg-background shadow-soft"
                />
              )}
              <span className="relative">{item.label}</span>
            </button>
          );
        })}
      </div>
      {current && (
        <motion.div
          key={current.id}
          id={`${baseId}-${current.id}-panel`}
          role="tabpanel"
          aria-labelledby={`${baseId}-${current.id}-tab`}
          tabIndex={0}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {current.content}
        </motion.div>
      )}
    </div>
  );
}

/* ---------- Progress ---------- */

interface ProgressProps {
  value: number;
  label: string;
  showValue?: boolean;
  tone?: 'primary' | 'accent' | 'success';
  className?: string;
}

const progressTones = { primary: 'bg-primary', accent: 'bg-accent', success: 'bg-success' } as const;

export function Progress({ value, label, showValue, tone = 'primary', className }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn('grid gap-1.5', className)}>
      {showValue && (
        <div className="flex justify-between text-caption text-muted-foreground">
          <span>{label}</span>
          <span className="tabular-nums">{Math.round(clamped)}%</span>
        </div>
      )}
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped)}
        className="h-2.5 overflow-hidden rounded-full bg-surface-muted"
      >
        <motion.div
          className={cn('h-full rounded-full', progressTones[tone])}
          initial={false}
          animate={{ width: `${clamped}%` }}
          transition={{ type: 'spring', stiffness: 120, damping: 22 }}
        />
      </div>
    </div>
  );
}
