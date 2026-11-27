'use client';

import { RotateCcw } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import Link from 'next/link';
import { useState } from 'react';
import { cn } from '@/lib/cn';
import { accuracyTone, percent } from '../format';
import type { ChapterStat } from '../types';

const grades = ['all', '10', '11', '12'] as const;
const barColor = { success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger' } as const;
const textColor = { success: 'text-success', warning: 'text-warning', danger: 'text-danger' } as const;

export function ChapterStats({ chapters }: { chapters: ChapterStat[] }) {
  const reduce = useReducedMotion();
  const [grade, setGrade] = useState<(typeof grades)[number]>('all');
  const shown = chapters.filter((entry) => grade === 'all' || String(entry.chapter.grade) === grade);

  return (
    <section aria-labelledby="chapter-title" className="grid content-start gap-4 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="chapter-title" className="text-h3 text-foreground">Theo từng chương</h2>
          <p className="mt-0.5 text-caption text-muted-foreground">Chương yếu nhất ở trên cùng.</p>
        </div>
        <div role="group" aria-label="Lọc theo lớp" className="flex rounded-full bg-surface-muted p-1">
          {grades.map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={grade === value}
              onClick={() => setGrade(value)}
              className={cn(
                'min-h-8 rounded-full px-3 text-caption font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                grade === value ? 'bg-background text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {value === 'all' ? 'Tất cả' : `Lớp ${value}`}
            </button>
          ))}
        </div>
      </div>
      {shown.length === 0 ? (
        <p className="py-6 text-label text-muted-foreground" role="status">Chưa có bài làm cho bộ lọc này.</p>
      ) : (
        <ul className="grid gap-1">
          {shown.map(({ chapter, correct, total }, index) => {
            const ratio = total > 0 ? correct / total : 0;
            const tone = accuracyTone(ratio);
            const needsPractice = total > 0 && ratio < 0.75;
            return (
              <li key={chapter.code} className="-mx-2 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-xl px-2 py-2.5 transition-colors hover:bg-surface">
                <div className="grid gap-2">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-label font-semibold text-foreground">{chapter.name}</p>
                    <p className={cn('text-label font-bold tabular-nums', textColor[tone])}>{percent(ratio)}</p>
                  </div>
                  <div
                    role="meter"
                    aria-label={`Tỉ lệ đúng: ${chapter.name}`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(ratio * 100)}
                    className="h-2.5 overflow-hidden rounded-full bg-surface-muted"
                  >
                    <motion.div
                      className={cn('h-full rounded-full', barColor[tone])}
                      initial={reduce ? false : { width: 0 }}
                      whileInView={{ width: percent(ratio) }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: Math.min(index, 8) * 0.05, ease: [0.16, 1, 0.3, 1] }}
                      style={reduce ? { width: percent(ratio) } : undefined}
                    />
                  </div>
                  <p className="text-caption tabular-nums text-muted-foreground">Lớp {chapter.grade} · {correct}/{total} câu đúng</p>
                </div>
                {needsPractice ? (
                  <Link
                    href={`/exams/new?q=${encodeURIComponent(`Ôn chương ${chapter.name}`)}`}
                    aria-label={`Ôn lại chương ${chapter.name}`}
                    className="inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-subtle px-3 text-caption font-semibold whitespace-nowrap text-primary transition-colors hover:bg-primary hover:text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    <RotateCcw aria-hidden="true" className="size-3.5" />
                    Ôn lại
                  </Link>
                ) : (
                  <span className="inline-flex min-h-9 w-[5.25rem] items-center justify-center text-caption text-muted-foreground">Đã vững</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
