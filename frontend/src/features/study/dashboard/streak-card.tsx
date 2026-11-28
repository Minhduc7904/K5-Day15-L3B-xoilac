'use client';

import { Check } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { cn } from '@/lib/cn';
import { Flame } from '../components/flame';
import type { DashboardData } from '../types';
import { CountUp } from './count-up';

const WEEKDAY = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];

/** Chuỗi ngày học, đặt ở cột phải của đầu trang (nền navy). */
export function StudyStreak({ streak }: { streak: DashboardData['streak'] }) {
  const reduce = useReducedMotion();
  const week = streak.days.slice(-7);
  const studiedToday = week.at(-1)?.studied ?? false;
  const lit = streak.current > 0;
  const message = streak.current === 0
    ? 'Làm một đề để nhóm lửa chuỗi đầu tiên.'
    : !studiedToday
      ? 'Hôm nay chưa học. Làm một đề để giữ lửa nhé!'
      : streak.current >= streak.best
        ? 'Bạn đang ở kỷ lục của chính mình!'
        : `Còn ${streak.best - streak.current} ngày nữa là chạm kỷ lục.`;

  return (
    <section
      aria-labelledby="streak-title"
      className="grid content-between gap-5 rounded-2xl bg-foreground/25 p-5 lg:rounded-none lg:rounded-r-3xl lg:p-7"
    >
      <div>
        <h2 id="streak-title" className="flex items-baseline justify-between gap-3 text-label font-semibold text-primary-foreground/85">
          Chuỗi ngày học
          <span className="text-caption font-normal text-primary-foreground/70">Kỷ lục {streak.best} ngày</span>
        </h2>
        <div className="mt-3 flex items-end gap-3">
          <Flame lit={lit} size={52} className="shrink-0 drop-shadow-[0_6px_12px_rgb(249_115_22/0.45)]" />
          <p className="flex items-baseline gap-2">
            <strong className="text-6xl leading-none font-bold tracking-tight">
              <CountUp value={streak.current} delay={0.3} />
            </strong>
            <span className="text-label font-semibold text-primary-foreground/85">ngày liên tiếp</span>
          </p>
        </div>
      </div>

      <ol className="grid grid-cols-7 gap-1" aria-label="7 ngày gần nhất">
        {week.map((day, index) => {
          const date = new Date(day.date);
          const isToday = index === week.length - 1;
          return (
            <li key={day.date} aria-current={isToday ? 'date' : undefined} className="grid justify-items-center gap-1.5">
              <span className="sr-only">
                {date.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'numeric' })}, {day.studied ? 'đã học' : 'chưa học'}
              </span>
              <motion.span
                aria-hidden="true"
                initial={reduce ? false : { scale: 0.4, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 420, damping: 18, delay: 0.45 + index * 0.06 }}
                className={cn(
                  'grid size-8 place-items-center rounded-full',
                  day.studied
                    ? 'bg-[linear-gradient(to_top,var(--color-flame-strong),var(--color-flame))] text-primary-foreground shadow-[0_4px_10px_-2px_rgb(249_115_22/0.6)]'
                    : 'border border-dashed border-primary-foreground/35',
                  isToday && 'ring-2 ring-ember ring-offset-2 ring-offset-primary',
                )}
              >
                {day.studied && <Check className="size-4" strokeWidth={3} />}
              </motion.span>
              <span aria-hidden="true" className={cn('text-[0.6875rem]', isToday ? 'font-semibold text-ember' : 'text-primary-foreground/70')}>
                {isToday ? 'Nay' : WEEKDAY[date.getDay()]}
              </span>
            </li>
          );
        })}
      </ol>

      <p className="text-caption text-primary-foreground/80">{message}</p>
    </section>
  );
}
