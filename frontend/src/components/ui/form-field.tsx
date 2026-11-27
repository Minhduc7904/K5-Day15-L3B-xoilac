'use client';

import { CircleAlert } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useId, type ComponentProps, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface LabelProps extends ComponentProps<'label'> {
  required?: boolean;
}

export function Label({ required, className, children, ...props }: LabelProps) {
  return (
    <label className={cn('text-label text-foreground', className)} {...props}>
      {children}
      {required && (
        <span className="ml-0.5 text-danger" aria-hidden="true">
          *
        </span>
      )}
    </label>
  );
}

export interface FieldControlProps {
  id: string;
  invalid: boolean;
  required?: boolean;
  'aria-describedby'?: string;
}

interface FormFieldProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  required?: boolean;
  id?: string;
  className?: string;
  /** Nhận id và thuộc tính a11y để gắn vào ô nhập. */
  children: (field: FieldControlProps) => ReactNode;
}

/** Nhãn + ô nhập + gợi ý + lỗi. Lỗi được gắn bằng aria-describedby nên trình đọc màn hình đọc cùng ô nhập. */
export function FormField({ label, hint, error, required, id, className, children }: FormFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={cn('grid gap-1.5', className)}>
      <Label htmlFor={fieldId} required={required}>
        {label}
      </Label>
      {children({ id: fieldId, invalid: Boolean(error), required, 'aria-describedby': describedBy })}
      {hint && !error && (
        <p id={hintId} className="text-caption text-muted-foreground">
          {hint}
        </p>
      )}
      <AnimatePresence initial={false}>
        {error && (
          <motion.p
            key="error"
            id={errorId}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
            className="flex items-center gap-1.5 text-caption font-medium text-danger"
          >
            <CircleAlert className="size-3.5 shrink-0" aria-hidden="true" />
            {error}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}
