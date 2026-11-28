'use client';

import { RotateCcw } from 'lucide-react';
import Image from 'next/image';
import type { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="grid min-w-0 gap-1.5">
        {eyebrow && <p className="text-label font-semibold text-accent-strong">{eyebrow}</p>}
        <h1 className="text-h1 text-balance text-foreground">{title}</h1>
        {description && <p className="max-w-2xl text-body text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function PageContainer({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10', className)}>{children}</div>;
}

export function ErrorState({ title = 'Chưa tải được dữ liệu', message, onRetry }: { title?: string; message?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="grid justify-items-center gap-3 rounded-3xl border border-border bg-background px-6 py-12 text-center">
      <Image src="/brand/mascot/static/studying.webp" alt="" width={384} height={384} className="h-auto w-28 opacity-90" />
      <h2 className="text-h3 text-foreground">{title}</h2>
      <p className="max-w-md text-body text-muted-foreground">{message ?? 'Có thể mạng đang chập chờn. Bạn thử lại nhé.'}</p>
      {onRetry && (
        <Button variant="outline" leftIcon={<RotateCcw aria-hidden="true" />} onClick={onRetry}>
          Thử lại
        </Button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
  mascot = 'welcome',
}: {
  title: string;
  message?: string;
  action?: ReactNode;
  mascot?: 'welcome' | 'studying' | 'working';
}) {
  return (
    <div className="grid justify-items-center gap-3 rounded-3xl border-2 border-dashed border-border bg-background/60 px-6 py-12 text-center">
      <Image src={`/brand/mascot/static/${mascot}.webp`} alt="" width={384} height={384} className="h-auto w-28" />
      <h2 className="text-h3 text-foreground">{title}</h2>
      {message && <p className="max-w-md text-body text-muted-foreground">{message}</p>}
      {action}
    </div>
  );
}
