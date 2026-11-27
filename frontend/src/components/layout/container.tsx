import type { ComponentProps, ReactNode } from 'react';
import { cn } from '@/lib/cn';

const widths = { md: 'max-w-3xl', lg: 'max-w-5xl', xl: 'max-w-6xl', full: 'max-w-7xl' } as const;

interface ContainerProps extends ComponentProps<'div'> {
  size?: keyof typeof widths;
}

export function Container({ size = 'xl', className, ...props }: ContainerProps) {
  return <div className={cn('mx-auto w-full px-4 sm:px-6 lg:px-8', widths[size], className)} {...props} />;
}

const tones = {
  default: 'bg-background',
  surface: 'bg-surface',
  inverse: 'bg-foreground text-primary-foreground',
} as const;

interface SectionProps extends ComponentProps<'section'> {
  tone?: keyof typeof tones;
}

export function Section({ tone = 'default', className, ...props }: SectionProps) {
  return <section className={cn('relative py-20 sm:py-28', tones[tone], className)} {...props} />;
}

interface SectionHeaderProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  align?: 'center' | 'left';
  /** Đặt id cho tiêu đề để section dùng aria-labelledby. */
  titleId?: string;
  inverse?: boolean;
  className?: string;
}

export function SectionHeader({ eyebrow, title, description, align = 'center', titleId, inverse, className }: SectionHeaderProps) {
  return (
    <div className={cn('grid max-w-2xl gap-4', align === 'center' && 'mx-auto justify-items-center text-center', className)}>
      {eyebrow && (
        <p
          className={cn(
            'inline-flex items-center gap-2 text-label font-semibold tracking-wide uppercase',
            inverse ? 'text-accent' : 'text-accent-strong',
          )}
        >
          <span className="h-px w-6 bg-current" aria-hidden="true" />
          {eyebrow}
        </p>
      )}
      <h2 id={titleId} className={cn('text-h1 text-balance', inverse ? 'text-primary-foreground' : 'text-foreground')}>
        {title}
      </h2>
      {description && (
        <p className={cn('text-body-lg text-pretty', inverse ? 'text-primary-foreground/75' : 'text-muted-foreground')}>
          {description}
        </p>
      )}
    </div>
  );
}
