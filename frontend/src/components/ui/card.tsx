import type { ComponentProps } from 'react';
import { cn } from '@/lib/cn';

const variants = {
  default: 'border border-border bg-background shadow-soft',
  muted: 'border border-border bg-surface',
  elevated: 'bg-background shadow-lift',
  outline: 'border-2 border-dashed border-border bg-transparent',
} as const;

interface CardProps extends ComponentProps<'div'> {
  variant?: keyof typeof variants;
  /** Nổi lên khi rê chuột, dùng cho thẻ bấm được. */
  interactive?: boolean;
}

export function Card({ variant = 'default', interactive, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-3xl',
        variants[variant],
        interactive && 'transition-[translate,box-shadow,border-color] duration-300 ease-out hover:-translate-y-1 hover:border-primary/30 hover:shadow-lift',
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid gap-1.5 p-6 pb-0', className)} {...props} />;
}

export function CardTitle({ className, ...props }: ComponentProps<'h3'>) {
  return <h3 className={cn('text-h3 text-foreground', className)} {...props} />;
}

export function CardDescription({ className, ...props }: ComponentProps<'p'>) {
  return <p className={cn('text-body text-muted-foreground', className)} {...props} />;
}

export function CardContent({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('p-6', className)} {...props} />;
}

export function CardFooter({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('flex items-center gap-3 border-t border-border px-6 py-4', className)} {...props} />;
}
