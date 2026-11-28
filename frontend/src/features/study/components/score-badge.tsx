import { cn } from '@/lib/cn';
import { scoreTone } from '../format';
import { formatScore } from '../grading';

const tones = {
  success: 'bg-success-subtle text-success',
  primary: 'bg-primary-subtle text-primary',
  warning: 'bg-warning-subtle text-warning',
  danger: 'bg-danger-subtle text-danger',
};

export function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={cn('flex size-12 shrink-0 flex-col items-center justify-center rounded-2xl text-body-lg font-bold tabular-nums', tones[scoreTone(score)])}>
      {formatScore(score)}
      <span className="sr-only"> điểm</span>
    </span>
  );
}

