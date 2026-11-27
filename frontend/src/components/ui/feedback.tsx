import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type Tone = 'info' | 'success' | 'warning' | 'danger';

const alertTones: Record<Tone, { box: string; icon: string; Icon: typeof Info }> = {
  info: { box: 'border-info/20 bg-info-subtle', icon: 'text-info', Icon: Info },
  success: { box: 'border-success/20 bg-success-subtle', icon: 'text-success', Icon: CircleCheck },
  warning: { box: 'border-warning/25 bg-warning-subtle', icon: 'text-warning', Icon: TriangleAlert },
  danger: { box: 'border-danger/20 bg-danger-subtle', icon: 'text-danger', Icon: CircleAlert },
};

interface AlertProps {
  tone?: Tone;
  title: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  onDismiss?: () => void;
  className?: string;
}

/** Thông báo trong trang. Cảnh báo và lỗi dùng role="alert" để được đọc ngay. */
export function Alert({ tone = 'info', title, children, action, onDismiss, className }: AlertProps) {
  const { box, icon, Icon } = alertTones[tone];

  return (
    <div
      role={tone === 'danger' || tone === 'warning' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-2xl border p-4', box, className)}
    >
      <Icon className={cn('mt-0.5 size-5 shrink-0', icon)} aria-hidden="true" />
      <div className="grid flex-1 gap-1">
        <p className={cn('text-label font-semibold', icon)}>{title}</p>
        {children && <div className="text-body text-foreground">{children}</div>}
        {action && <div className="mt-2">{action}</div>}
      </div>
      {onDismiss && (
        <button
          type="button"
          aria-label="Đóng thông báo"
          onClick={onDismiss}
          className="-m-1 inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'animate-shimmer rounded-lg bg-[length:200%_100%]',
        'bg-[linear-gradient(90deg,var(--color-surface-muted)_25%,var(--color-surface)_50%,var(--color-surface-muted)_75%)]',
        className,
      )}
    />
  );
}

export type BadgeTone = 'neutral' | 'primary' | 'accent' | Tone;

const badgeTones: Record<BadgeTone, string> = {
  neutral: 'bg-surface-muted text-muted-foreground',
  primary: 'bg-primary-subtle text-primary',
  accent: 'bg-accent-subtle text-accent-strong',
  info: 'bg-info-subtle text-info',
  success: 'bg-success-subtle text-success',
  warning: 'bg-warning-subtle text-warning',
  danger: 'bg-danger-subtle text-danger',
};

interface BadgeProps {
  tone?: BadgeTone;
  dot?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Badge({ tone = 'neutral', dot, icon, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption font-semibold [&_svg]:size-3.5',
        badgeTones[tone],
        className,
      )}
    >
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {icon}
      {children}
    </span>
  );
}
