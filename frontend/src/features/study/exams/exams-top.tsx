'use client';

import { ArrowRight, ListTree, Play, Plus } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { typeColor, typeLabels } from '../labels';
import { chapterOf } from '../chapters';
import { examDuration, relativeDay, scoreTone } from '../format';
import { formatScore } from '../grading';
import type { ExamSummary } from '../types';

const TARGET = 8;
const ease = [0.16, 1, 0.3, 1] as const;
const scoreText = { success: 'text-success', primary: 'text-primary', warning: 'text-warning', danger: 'text-danger' } as const;

/** Đầu trang: tiêu đề, tiến độ làm đề, nút tạo đề. */
export function ExamsHeader({ exams }: { exams: ExamSummary[] | null }) {
  const total = exams?.length ?? 0;
  const done = exams?.filter((e) => e.attempts > 0).length ?? 0;
  const reached = exams?.filter((e) => (e.bestScore ?? 0) >= TARGET).length ?? 0;

  return (
    <header className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <div className="grid gap-3">
        <h1 className="text-h1 text-foreground">Đề của tôi</h1>
        {exams && total > 0 ? (
          <div className="grid max-w-md gap-2">
            <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={`Đã làm ${done} trên ${total} đề, ${reached} đề đạt từ ${TARGET} điểm`}>
              {[...exams]
                .sort((a, b) => Number(b.attempts > 0) - Number(a.attempts > 0) || (b.bestScore ?? 0) - (a.bestScore ?? 0))
                .map((e) => (
                  <span
                    key={e.id}
                    className={cn('flex-1 first:rounded-l-full last:rounded-r-full', e.attempts === 0 ? 'bg-surface-muted' : (e.bestScore ?? 0) >= TARGET ? 'bg-success' : 'bg-primary')}
                  />
                ))}
            </div>
            <p className="text-label text-muted-foreground">
              Đã làm <b className="font-semibold text-foreground tabular-nums">{done}/{total}</b> đề
              {reached > 0 && <>, <b className="font-semibold text-success tabular-nums">{reached}</b> đề đạt từ {TARGET} điểm</>}.
            </p>
          </div>
        ) : (
          <p className="text-body text-muted-foreground">{exams ? 'Chưa có đề nào. Nhắn Examind để tạo đề đầu tiên.' : 'Đang tải…'}</p>
        )}
      </div>
      <Button href="/exams/new" leftIcon={<Plus aria-hidden="true" />} className="justify-self-start sm:justify-self-end">
        Tạo đề mới
      </Button>
    </header>
  );
}

/** Đề nên làm tiếp: đề chưa làm mới nhất, rồi tới đề có điểm cao nhất còn dưới mục tiêu, cuối cùng là đề làm gần nhất. */
export function pickNext(exams: ExamSummary[]): { exam: ExamSummary; reason: string; cta: string } | null {
  const byNewest = [...exams].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const todo = byNewest.find((e) => e.attempts === 0);
  if (todo) {
    return { exam: todo, reason: `Đề này tạo ${relativeDay(todo.createdAt).toLowerCase()}, bạn chưa làm. Làm luôn khi còn nhớ bài nhé!`, cta: 'Làm bài ngay' };
  }
  const below = exams.filter((e) => e.bestScore !== null && e.bestScore < TARGET).sort((a, b) => (a.bestScore ?? 0) - (b.bestScore ?? 0))[0];
  if (below) {
    return { exam: below, reason: `Lần cao nhất bạn được ${formatScore(below.bestScore!)} điểm. Làm lại một lượt để vượt mốc ${TARGET} nhé!`, cta: 'Làm lại' };
  }
  const recent = exams[0];
  return recent ? { exam: recent, reason: 'Bạn đã vượt mục tiêu ở mọi đề. Ôn lại đề gần nhất để giữ phong độ.', cta: 'Ôn lại' } : null;
}

/** Thẻ lớn đầu trang: linh vật gợi ý đề nên làm tiếp. */
export function NextExamCard({ pick, onStructure }: { pick: NonNullable<ReturnType<typeof pickNext>>; onStructure: () => void }) {
  const reduce = useReducedMotion();
  const { exam } = pick;
  const parts = exam.sections.map((s) => ({ type: s.type, n: s.questionIds.length })).filter((p) => p.n > 0);

  return (
    <section aria-labelledby="next-title" className="relative isolate flex flex-col overflow-hidden rounded-3xl bg-primary text-primary-foreground shadow-lift">
      <div aria-hidden="true" className="bg-grid-inverse absolute inset-0 -z-10 [mask-image:linear-gradient(to_bottom,black,transparent_90%)]" />
      <div className="flex flex-1 flex-col gap-5 p-5 sm:p-7">
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-3 sm:gap-4">
          <motion.div
            className="w-20 sm:w-24"
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
          >
            <motion.div animate={reduce ? undefined : { y: [0, -5, 0] }} transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}>
              <Image src="/brand/mascot/static/working.webp" alt="" width={192} height={192} unoptimized className="pixelated h-auto w-full drop-shadow-[0_10px_14px_rgb(3_23_47/0.45)]" />
            </motion.div>
          </motion.div>
          <motion.p
            className="relative mb-4 max-w-md rounded-2xl rounded-bl-sm bg-background px-4 py-3 text-label text-foreground shadow-soft"
            initial={reduce ? false : { opacity: 0, scale: 0.94, x: -6 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
            style={{ originX: 0, originY: 1 }}
          >
            <svg aria-hidden="true" viewBox="0 0 14 14" className="absolute -left-[11px] bottom-0 size-3.5 fill-background">
              <path d="M14 0v14H0C7 12 12 7 14 0z" />
            </svg>
            {pick.reason}
          </motion.p>
        </div>

        <div className="grid gap-2">
          <h2 id="next-title" className="text-h2 text-balance">
            <Link href={`/exams/${exam.id}`} className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              {exam.title}
            </Link>
          </h2>
          <p className="text-label text-primary-foreground/80">
            {exam.questionCount} câu · {examDuration(exam.durationMinutes)} · {exam.chapters.map((c) => chapterOf(c).name).join(', ')}
          </p>
        </div>

        <div className="grid gap-1.5">
          <div className="flex h-2 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
            {parts.map((p) => (
              <span key={p.type} className={cn('first:rounded-l-full last:rounded-r-full', typeColor[p.type] === 'bg-primary' ? 'bg-primary-foreground' : typeColor[p.type])} style={{ width: `${(p.n / exam.questionCount) * 100}%` }} />
            ))}
          </div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-primary-foreground/80">
            {parts.map((p) => (
              <li key={p.type}>
                {typeLabels[p.type]} <b className="font-semibold text-primary-foreground tabular-nums">{p.n}</b>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-auto flex flex-wrap items-center gap-2 pt-1">
          <Link
            href={`/exams/${exam.id}`}
            className="group inline-flex h-11 items-center gap-2 rounded-xl bg-flame-strong px-5 text-label font-semibold text-primary-foreground transition-[background-color,transform] hover:bg-danger-hover active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <Play className="size-4" aria-hidden="true" /> Xem đề
          </Link>
          <button
            type="button"
            onClick={onStructure}
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-primary-foreground/25 px-4 text-label font-semibold text-primary-foreground transition-colors hover:border-primary-foreground/60 hover:bg-primary-foreground/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <ListTree className="size-4" aria-hidden="true" /> Xem cấu trúc
          </button>
        </div>
      </div>
    </section>
  );
}

/** Cột phải: các đề mới tạo gần đây. */
export function RecentExams({ exams, onStructure }: { exams: ExamSummary[]; onStructure: (exam: ExamSummary) => void }) {
  return (
    <section aria-labelledby="recent-exams-title" className="flex flex-col rounded-3xl bg-background p-5 shadow-soft sm:p-6">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 id="recent-exams-title" className="text-h3 text-foreground">Mới tạo</h2>
        <Link href="/exams/new" className="inline-flex items-center gap-1 rounded-sm text-label font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          Tạo thêm <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </div>
      {exams.length === 0 ? (
        <p className="py-6 text-label text-muted-foreground">Đề bạn tạo với AI sẽ hiện ở đây.</p>
      ) : (
        <ol className="grid gap-1">
          {exams.map((exam) => {
            const parts = exam.sections.map((s) => ({ type: s.type, n: s.questionIds.length })).filter((p) => p.n > 0);
            return (
              <li key={exam.id} className="group relative -mx-2 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-surface">
                <div className="grid min-w-0 gap-1.5">
                  <Link
                    href={`/exams/${exam.id}`}
                    className="truncate rounded-sm text-label font-semibold text-foreground after:absolute after:inset-0 after:rounded-xl group-hover:text-primary focus-visible:outline-none group-has-[a:focus-visible]:underline"
                  >
                    {exam.title}
                  </Link>
                  <div className="flex items-center gap-2 text-caption text-muted-foreground">
                    <span className="flex h-1.5 w-12 shrink-0 gap-px overflow-hidden rounded-full" aria-hidden="true">
                      {parts.map((p) => (
                        <span key={p.type} className={typeColor[p.type]} style={{ width: `${(p.n / exam.questionCount) * 100}%` }} />
                      ))}
                    </span>
                    <span className="truncate">{relativeDay(exam.createdAt)} · {exam.questionCount} câu · {examDuration(exam.durationMinutes)}</span>
                  </div>
                </div>
                <div className="relative z-10 flex items-center gap-1">
                  {exam.bestScore !== null ? (
                    <span className={cn('w-10 text-right text-body font-bold tabular-nums', scoreText[scoreTone(exam.bestScore)])}>{formatScore(exam.bestScore)}</span>
                  ) : (
                    <span className="rounded-full bg-accent-subtle px-2 py-0.5 text-[0.6875rem] font-semibold whitespace-nowrap text-accent-strong">Chưa làm</span>
                  )}
                  <button
                    type="button"
                    onClick={() => onStructure(exam)}
                    aria-label={`Xem cấu trúc “${exam.title}”`}
                    title="Xem cấu trúc"
                    className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-background hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <ListTree className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
