import type { ComponentProps, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export const fieldBase =
  'w-full rounded-xl border bg-background text-body text-foreground placeholder:text-muted-foreground ' +
  'transition-[border-color,box-shadow,background-color] duration-150 outline-none ' +
  'focus-visible:ring-4 disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-70';

export function fieldState(invalid?: boolean) {
  return invalid
    ? 'border-danger focus-visible:border-danger focus-visible:ring-danger/15'
    : 'border-input hover:border-primary/60 focus-visible:border-ring focus-visible:ring-ring/20';
}

export interface InputProps extends ComponentProps<'input'> {
  invalid?: boolean;
  /** Icon trang trí bên trái ô nhập. */
  leftIcon?: ReactNode;
  /** Vùng bên phải, ví dụ nút hiện mật khẩu. */
  rightSlot?: ReactNode;
}

export function Input({ invalid, leftIcon, rightSlot, className, ...props }: InputProps) {
  return (
    <div className="relative">
      {leftIcon && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-muted-foreground [&_svg]:size-[18px]"
        >
          {leftIcon}
        </span>
      )}
      <input
        aria-invalid={invalid || undefined}
        className={cn(fieldBase, fieldState(invalid), 'h-11 px-3.5', Boolean(leftIcon) && 'pl-10', Boolean(rightSlot) && 'pr-12', className)}
        {...props}
      />
      {rightSlot && <span className="absolute inset-y-0 right-1 flex items-center">{rightSlot}</span>}
    </div>
  );
}

export interface TextareaProps extends ComponentProps<'textarea'> {
  invalid?: boolean;
}

export function Textarea({ invalid, className, rows = 4, ...props }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(fieldBase, fieldState(invalid), 'min-h-24 resize-y px-3.5 py-2.5', className)}
      {...props}
    />
  );
}
