'use client';

import { X } from 'lucide-react';
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { IconButton } from './button';

interface ModalProps {
  open: boolean;
  title: string;
  description?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}

/** Hộp thoại dùng <dialog> gốc của trình duyệt: có bẫy focus, Esc để đóng và nền mờ sẵn. */
export function Modal({ open, title, description, onClose, children, className }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      className={cn(
        'm-auto w-[min(32rem,calc(100vw-2rem))] rounded-2xl border border-border bg-background p-0 text-foreground shadow-lift backdrop:bg-foreground/40',
        className,
      )}
    >
      {open && (
        <div className="grid gap-4 p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="grid gap-1">
              <h2 id={titleId} className="text-body-lg font-semibold">
                {title}
              </h2>
              {description && <p className="text-label text-muted-foreground">{description}</p>}
            </div>
            <IconButton label="Đóng" size="sm" onClick={onClose}>
              <X aria-hidden="true" />
            </IconButton>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
