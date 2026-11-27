'use client';

import { motion } from 'motion/react';
import { cn } from '@/lib/cn';
import { passwordStrength } from '../validation';

const levels = [
  { label: '', bar: '', text: '' },
  { label: 'Yếu', bar: 'bg-danger', text: 'text-danger' },
  { label: 'Trung bình', bar: 'bg-warning', text: 'text-warning' },
  { label: 'Khá', bar: 'bg-info', text: 'text-info' },
  { label: 'Mạnh', bar: 'bg-success', text: 'text-success' },
];

export function PasswordStrength({ password }: { password: string }) {
  const score = passwordStrength(password);
  const level = levels[score];

  return (
    <div className="grid gap-1.5" aria-live="polite">
      <div className="grid grid-cols-4 gap-1.5" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
            <motion.span
              className={cn('block h-full rounded-full', level.bar)}
              initial={false}
              animate={{ width: score >= i ? '100%' : '0%' }}
              transition={{ duration: 0.3, delay: (i - 1) * 0.04 }}
            />
          </span>
        ))}
      </div>
      {score > 0 && (
        <p className="text-caption text-muted-foreground">
          Độ mạnh: <span className={cn('font-semibold', level.text)}>{level.label}</span>
          {score < 3 && ' · Thêm chữ số, chữ hoa hoặc ký tự đặc biệt để mạnh hơn.'}
        </p>
      )}
    </div>
  );
}
