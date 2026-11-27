'use client';

import { Eye, ListTree, Play, X } from 'lucide-react';
import { motion } from 'motion/react';
import { Fragment, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { studyApi } from '../api';
import { DIFFS, TYPES } from '../create/plan';
import { diffColor, typeColor } from '../create/structure-preview';
import { chapterOf, difficultyLabels, typeLabels } from '../fixtures/chapters';
import { examDuration } from '../format';
import type { Difficulty, ExamSummary, QuestionType } from '../types';
import { useResource } from '../use-resource';

const PART = ['Phần I', 'Phần II', 'Phần III'];

/** Popup cấu trúc tổng quan của một đề: số câu theo phần × mức độ, và ma trận theo chương. */
export function ExamStructureDialog({ exam, onClose }: { exam: ExamSummary; onClose: () => void }) {
  const res = useResource(() => studyApi.getExam(exam.id), `exam-structure-${exam.id}`);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 grid items-end p-0 sm:place-items-center sm:p-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-foreground/45 backdrop-blur-[2px]" onClick={onClose} />
      <motion.div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="structure-title"
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 24 }}
        transition={{ type: 'spring', stiffness: 380, damping: 34 }}
        className="relative flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-2xl bg-background shadow-lift outline-none sm:max-w-2xl sm:rounded-2xl"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-accent-subtle text-accent-strong">
            <ListTree className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="structure-title" className="text-h3 text-balance text-foreground">{exam.title}</h2>
            <p className="text-caption text-muted-foreground">
              {exam.questionCount} câu · {examDuration(exam.durationMinutes)} · {exam.sections.length} phần
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {res.status === 'loading' && (
            <div className="grid gap-3" aria-busy="true" aria-label="Đang tải cấu trúc đề">
              <Skeleton className="h-28 rounded-xl" />
              <Skeleton className="h-40 rounded-xl" />
            </div>
          )}
          {res.status === 'error' && (
            <div role="alert" className="grid justify-items-start gap-2 rounded-xl bg-danger-subtle p-4 text-label text-foreground">
              Chưa tải được cấu trúc đề.
              <Button size="sm" variant="outline" onClick={res.reload}>Thử lại</Button>
            </div>
          )}
          {res.status === 'ready' && <Overview questions={res.data.questions} />}
        </div>

        <footer className="flex justify-end gap-2 border-t border-border px-5 py-3">
          <Button variant="outline" href={`/exams/${exam.id}`} leftIcon={<Eye aria-hidden="true" />}>Xem đề</Button>
          <Button href={`/exams/${exam.id}/take`} leftIcon={<Play aria-hidden="true" />}>{exam.attempts ? 'Làm lại' : 'Làm bài'}</Button>
        </footer>
      </motion.div>
    </div>
  );
}

type Q = { type: QuestionType; difficulty: Difficulty; chapter: string };

function Overview({ questions }: { questions: Q[] }) {
  const count = (filter: (q: Q) => boolean) => questions.filter(filter).length;
  const total = questions.length;
  const chapters = [...new Set(questions.map((q) => q.chapter))];
  const parts = TYPES.filter((t) => count((q) => q.type === t) > 0);

  return (
    <div className="grid gap-6">
      {/* Theo phần: mỗi phần một thanh chia theo mức độ */}
      <section aria-labelledby="by-part">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="by-part" className="text-label font-semibold text-foreground">Theo phần</h3>
          <ul className="flex flex-wrap gap-x-3 gap-y-1" aria-label="Chú thích mức độ">
            {DIFFS.map((d) => (
              <li key={d} className="flex items-center gap-1.5 text-caption text-muted-foreground">
                <i className={cn('size-2.5 rounded-full', diffColor[d])} aria-hidden="true" />
                {difficultyLabels[d]}
              </li>
            ))}
          </ul>
        </div>
        <ul className="grid gap-3">
          {parts.map((t, i) => {
            const n = count((q) => q.type === t);
            return (
              <li key={t} className="grid gap-1.5">
                <p className="flex items-baseline justify-between gap-3 text-caption">
                  <span className="flex items-center gap-1.5 font-semibold text-foreground">
                    <i className={cn('size-2.5 rounded-full', typeColor[t])} aria-hidden="true" />
                    {PART[TYPES.indexOf(t)] ?? `Phần ${i + 1}`} · {typeLabels[t]}
                  </span>
                  <span className="text-muted-foreground tabular-nums"><b className="font-semibold text-foreground">{n}</b> câu · {Math.round((n / total) * 100)}%</span>
                </p>
                <div className="flex h-6 overflow-hidden rounded-lg bg-surface-muted" style={{ width: `${Math.max(18, (n / total) * 100)}%` }}>
                  {DIFFS.map((d, k) => {
                    const m = count((q) => q.type === t && q.difficulty === d);
                    if (!m) return null;
                    return (
                      <motion.span
                        key={d}
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 0.5, delay: 0.1 + k * 0.06, ease: [0.16, 1, 0.3, 1] }}
                        style={{ width: `${(m / n) * 100}%`, originX: 0 }}
                        className={cn('flex items-center justify-center text-[0.6875rem] font-bold text-primary-foreground tabular-nums', diffColor[d])}
                        title={`${difficultyLabels[d]}: ${m} câu`}
                      >
                        {m}
                        <span className="sr-only"> câu {difficultyLabels[d]}</span>
                      </motion.span>
                    );
                  })}
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Ma trận theo chương */}
      <section aria-labelledby="by-chapter">
        <h3 id="by-chapter" className="mb-2 text-label font-semibold text-foreground">Theo chương</h3>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full min-w-[34rem] border-separate border-spacing-0 text-caption">
            <thead className="bg-surface">
              <tr>
                <th rowSpan={2} scope="col" className="border-b border-border px-3 py-2 text-left font-semibold text-foreground">Chương</th>
                {parts.map((t) => (
                  <th key={t} colSpan={4} scope="colgroup" className="border-l border-border px-2 pt-2 pb-0.5 text-center font-semibold text-foreground">
                    {PART[TYPES.indexOf(t)]}
                  </th>
                ))}
                <th rowSpan={2} scope="col" className="border-b border-l border-border px-2 text-center font-semibold text-foreground">Tổng</th>
              </tr>
              <tr>
                {parts.map((t) => (
                  <Fragment key={t}>
                    {DIFFS.map((d, k) => (
                      <th key={d} scope="col" className={cn('border-b border-border px-1 pb-1.5 text-center text-[0.6875rem] font-semibold text-muted-foreground', k === 0 && 'border-l')}>
                        {d}
                      </th>
                    ))}
                  </Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {chapters.map((c) => (
                <tr key={c} className="hover:bg-surface">
                  <th scope="row" className="border-b border-border px-3 py-2 text-left font-medium text-foreground">
                    <span className="line-clamp-2">{chapterOf(c).name}</span>
                  </th>
                  {parts.map((t) => (
                    <Fragment key={t}>
                      {DIFFS.map((d, k) => {
                        const m = count((q) => q.chapter === c && q.type === t && q.difficulty === d);
                        return (
                          <td key={d} className={cn('border-b border-border px-1 text-center tabular-nums', k === 0 && 'border-l', m ? 'font-bold text-foreground' : 'text-border')}>
                            {m || '·'}
                          </td>
                        );
                      })}
                    </Fragment>
                  ))}
                  <td className="border-b border-l border-border px-2 text-center font-bold text-foreground tabular-nums">{count((q) => q.chapter === c)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-surface">
              <tr>
                <th scope="row" className="px-3 py-2 text-left font-semibold text-foreground">Tổng</th>
                {parts.map((t) => (
                  <Fragment key={t}>
                    {DIFFS.map((d, k) => (
                      <td key={d} className={cn('px-1 text-center font-bold text-foreground tabular-nums', k === 0 && 'border-l border-border')}>
                        {count((q) => q.type === t && q.difficulty === d) || '·'}
                      </td>
                    ))}
                  </Fragment>
                ))}
                <td className="border-l border-border px-2 text-center text-label font-bold text-foreground tabular-nums">{total}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>
    </div>
  );
}
