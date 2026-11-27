import Link from 'next/link';
import type { ComponentProps, ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { Spinner } from './spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'accent' | 'danger' | 'inverse';
export type ButtonSize = 'sm' | 'md' | 'lg';

const base =
  'group/button relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-xl font-semibold ' +
  'transition-[background-color,border-color,color,box-shadow,translate,scale] duration-200 ease-out ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:scale-[0.97] ' +
  'disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 ' +
  '[&_svg]:size-[1.1em] [&_svg]:shrink-0';

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-primary-foreground shadow-soft hover:-translate-y-0.5 hover:bg-primary-hover hover:shadow-lift',
  secondary: 'bg-primary-subtle text-primary hover:bg-primary/15',
  outline: 'border border-input bg-background text-foreground hover:border-primary hover:text-primary',
  ghost: 'text-foreground hover:bg-surface-muted',
  accent: 'bg-accent text-foreground shadow-soft hover:-translate-y-0.5 hover:shadow-glow',
  danger: 'bg-danger text-primary-foreground shadow-soft hover:bg-danger-hover',
  /** Dùng trên nền tối (primary, foreground). */
  inverse: 'border border-primary-foreground/35 text-primary-foreground hover:bg-primary-foreground/10 focus-visible:outline-primary-foreground',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-3.5 text-label',
  md: 'h-11 px-5 text-label',
  lg: 'h-13 px-7 text-body font-semibold',
};

interface ButtonOptions {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  className?: string;
}

export function buttonClasses({ variant = 'primary', size = 'md', fullWidth, className }: ButtonOptions = {}) {
  return cn(base, variants[variant], sizes[size], fullWidth && 'w-full', className);
}

interface ButtonContentProps {
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  children?: ReactNode;
}

type NativeButtonProps = Omit<ComponentProps<'button'>, 'className' | 'children'>;
type LinkProps = Omit<ComponentProps<typeof Link>, 'className' | 'children' | 'href'>;

export type ButtonProps = ButtonOptions &
  ButtonContentProps &
  (({ href?: undefined } & NativeButtonProps) | ({ href: string } & LinkProps));

/**
 * Nút dùng chung. Truyền `href` để render thành link mà vẫn giữ kiểu nút.
 * `loading` khoá nút, hiện spinner và đặt `aria-busy`.
 */
export function Button(props: ButtonProps) {
  const { variant, size, fullWidth, className, loading = false, leftIcon, rightIcon, children, ...rest } = props;
  const classes = buttonClasses({ variant, size, fullWidth, className });
  const content = (
    <>
      {loading ? <Spinner size="sm" /> : leftIcon}
      {children !== undefined && <span>{children}</span>}
      {!loading && rightIcon}
    </>
  );

  if (rest.href !== undefined) {
    const { href, ...linkRest } = rest as { href: string } & LinkProps;
    return (
      <Link href={href} className={classes} {...linkRest}>
        {content}
      </Link>
    );
  }

  const { type = 'button', disabled, ...buttonRest } = rest as NativeButtonProps;
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={classes}
      {...buttonRest}
    >
      {content}
    </button>
  );
}

const iconSizes = { sm: 'size-9 rounded-lg', md: 'size-11 rounded-xl' } as const;
const iconVariants = {
  ghost: 'text-muted-foreground hover:bg-surface-muted hover:text-foreground',
  outline: 'border border-input bg-background text-foreground hover:border-primary hover:text-primary',
  secondary: 'bg-primary-subtle text-primary hover:bg-primary/15',
  primary: 'bg-primary text-primary-foreground hover:bg-primary-hover',
} as const;

interface IconButtonProps extends Omit<ComponentProps<'button'>, 'aria-label'> {
  /** Nhãn bắt buộc cho trình đọc màn hình vì nút không có chữ. */
  label: string;
  variant?: keyof typeof iconVariants;
  size?: keyof typeof iconSizes;
}

export function IconButton({ label, variant = 'ghost', size = 'md', type = 'button', className, children, ...props }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        'inline-flex shrink-0 items-center justify-center transition-[background-color,color,border-color,scale] duration-150',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:scale-95 disabled:pointer-events-none disabled:opacity-50',
        '[&_svg]:size-5',
        iconSizes[size],
        iconVariants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
