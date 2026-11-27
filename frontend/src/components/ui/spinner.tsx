import { cn } from '@/lib/cn';

const sizes = { sm: 'size-4', md: 'size-6', lg: 'size-10' } as const;

interface SpinnerProps {
  size?: keyof typeof sizes;
  /** Có nhãn thì spinner tự báo trạng thái cho trình đọc màn hình. Không có nhãn thì chỉ để trang trí. */
  label?: string;
  className?: string;
}

export function Spinner({ size = 'md', label, className }: SpinnerProps) {
  const svg = (
    <svg viewBox="0 0 24 24" fill="none" className={cn('animate-spin', sizes[size], className)} aria-hidden="true">
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21.5 12a9.5 9.5 0 0 0-9.5-9.5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );

  if (!label) return svg;

  return (
    <span role="status" className="inline-flex items-center gap-2">
      {svg}
      <span className="sr-only">{label}</span>
    </span>
  );
}
