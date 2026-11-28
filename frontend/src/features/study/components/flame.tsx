'use client';

import { motion, useReducedMotion } from 'motion/react';
import { useId } from 'react';
import { cn } from '@/lib/cn';

/**
 * Ngọn lửa của chuỗi ngày học. `lit=false` vẽ than tắt màu xám.
 * Lửa đang cháy lay nhẹ và đổi độ sáng; tắt khi người dùng bật giảm chuyển động.
 */
export function Flame({ lit = true, size = 40, className, intensity = 1 }: { lit?: boolean; size?: number; className?: string; intensity?: number }) {
  const id = useId().replace(/:/g, '');
  const reduce = useReducedMotion();
  const animate = lit && !reduce;

  return (
    <motion.svg
      viewBox="0 0 64 80"
      width={size}
      height={size * 1.25}
      aria-hidden="true"
      className={cn('overflow-visible', className)}
      style={{ originX: 0.5, originY: 1 }}
      animate={animate ? { scaleY: [1, 1.06 * intensity, 0.97, 1.03, 1], skewX: [0, -2, 1.5, -1, 0] } : undefined}
      transition={animate ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : undefined}
    >
      <defs>
        <linearGradient id={`outer-${id}`} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" style={{ stopColor: lit ? 'var(--color-flame-strong)' : 'var(--color-input)' }} />
          <stop offset="60%" style={{ stopColor: lit ? 'var(--color-flame)' : 'var(--color-border)' }} />
          <stop offset="100%" style={{ stopColor: lit ? 'var(--color-ember)' : 'var(--color-surface-muted)' }} />
        </linearGradient>
        <linearGradient id={`inner-${id}`} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" style={{ stopColor: lit ? 'var(--color-ember)' : 'var(--color-surface-muted)' }} />
          <stop offset="100%" style={{ stopColor: lit ? 'var(--color-background)' : 'var(--color-surface)' }} />
        </linearGradient>
      </defs>
      {lit && <ellipse cx="32" cy="74" rx="20" ry="4" style={{ fill: 'var(--color-flame)' }} opacity="0.18" />}
      <path
        d="M32 2c4 12 18 20 20 38 2 17-9 34-20 34S10 63 11 47c1-11 8-15 9-25 6 6 7 12 6 17 5-6 8-20 6-37z"
        fill={`url(#outer-${id})`}
      />
      <motion.path
        d="M32 36c3 6 10 10 10 20 0 9-5 16-10 16s-11-6-10-15c0-6 4-8 5-13 3 3 4 6 4 9 2-4 3-10 1-17z"
        fill={`url(#inner-${id})`}
        style={{ originX: 0.5, originY: 1 }}
        animate={animate ? { scaleY: [1, 1.12, 0.94, 1.08, 1], opacity: [0.95, 1, 0.85, 1, 0.95] } : undefined}
        transition={animate ? { duration: 1.1, repeat: Infinity, ease: 'easeInOut' } : undefined}
      />
    </motion.svg>
  );
}
