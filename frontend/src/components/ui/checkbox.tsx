'use client';

import { Check } from 'lucide-react';
import { motion } from 'motion/react';
import { useId, useState, type ComponentProps, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface CheckboxProps extends Omit<ComponentProps<'input'>, 'type'> {
  label: ReactNode;
  description?: ReactNode;
  invalid?: boolean;
}

export function Checkbox({
  label,
  description,
  invalid,
  id,
  className,
  disabled,
  'aria-describedby': extraDescribedBy,
  ...props
}: CheckboxProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const descId = description ? `${inputId}-desc` : undefined;
  const describedBy = [descId, extraDescribedBy].filter(Boolean).join(' ') || undefined;

  return (
    <label
      htmlFor={inputId}
      className={cn('group flex items-start gap-3', disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer', className)}
    >
      <span className="relative mt-0.5 flex size-5 shrink-0">
        <input
          id={inputId}
          type="checkbox"
          disabled={disabled}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className={cn(
            'peer size-5 cursor-[inherit] appearance-none rounded-md border-2 bg-background transition-colors duration-150',
            'checked:border-primary checked:bg-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
            invalid ? 'border-danger' : 'border-input group-hover:border-primary',
          )}
          {...props}
        />
        <Check
          strokeWidth={3.5}
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 m-auto size-3.5 scale-50 text-primary-foreground opacity-0 transition-[opacity,scale] duration-150 peer-checked:scale-100 peer-checked:opacity-100"
        />
      </span>
      <span className="grid gap-0.5">
        <span className="text-label text-foreground">{label}</span>
        {description && (
          <span id={descId} className="text-caption text-muted-foreground">
            {description}
          </span>
        )}
      </span>
    </label>
  );
}

interface SwitchProps {
  label: ReactNode;
  description?: ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function Switch({ label, description, checked, defaultChecked = false, onCheckedChange, disabled, className }: SwitchProps) {
  const [inner, setInner] = useState(defaultChecked);
  const isOn = checked ?? inner;
  const labelId = useId();

  const toggle = () => {
    if (checked === undefined) setInner(!isOn);
    onCheckedChange?.(!isOn);
  };

  return (
    <div className={cn('flex items-start justify-between gap-4', disabled && 'opacity-60', className)}>
      <span className="grid gap-0.5">
        <span id={labelId} className="text-label text-foreground">
          {label}
        </span>
        {description && <span className="text-caption text-muted-foreground">{description}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={isOn}
        aria-labelledby={labelId}
        disabled={disabled}
        onClick={toggle}
        className={cn(
          'relative inline-flex h-7 w-12 shrink-0 items-center rounded-full p-1 transition-colors duration-200',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed',
          isOn ? 'justify-end bg-primary' : 'justify-start bg-input',
        )}
      >
        <motion.span
          layout
          transition={{ type: 'spring', stiffness: 600, damping: 34 }}
          className="block size-5 rounded-full bg-background shadow-soft"
        />
      </button>
    </div>
  );
}
