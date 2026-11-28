'use client';

import { Library, ListTree, Play, Plus, Search, Sparkles } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { studyApi } from '../api';
import { EmptyState, ErrorState, PageContainer } from '../components/page-states';
import { typeColor } from '../labels';
import { chapterOf } from '../chapters';
import { examDuration, relativeDay, scoreTone } from '../format';
import { formatScore } from '../grading';
import type { ExamSummary } from '../types';
import { useResource } from '../use-resource';
import { ExamStructureDialog } from './exam-structure-dialog';
import { ExamsHeader, NextExamCard, pickNext, RecentExams } from './exams-top';

const FILTERS = [
  { id: 'all', label: 'Tất cả' },
  { id: 'todo', label: 'Chưa làm' },
  { id: 'done', label: 'Đã làm' },
  { id: 'ai', label: 'Tạo bằng AI' },
] as const;

type Filter = (typeof FILTERS)[number]['id'];

export function ExamsListPage() {
  const res = useResource(() => studyApi.listExams(), 'exams');
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const [structureOf, setStructureOf] = useState<ExamSummary | null>(null);

  const list = useMemo(() => {
    if (res.status !== 'ready') return [];
    const q = query.trim().toLowerCase();
    return res.data.filter((e) => {
      if (filter === 'todo' && e.attempts > 0) return false;
      if (filter === 'done' && e.attempts === 0) return false;
      if (filter === 'ai' && e.source !== 'ai') return false;
      if (!q) return true;
      return e.title.toLowerCase().includes(q) || e.chapters.some((c) => chapterOf(c).name.toLowerCase().includes(q));
    });
  }, [res, filter, query]);

  const counts = res.status === 'ready'
    ? { all: res.data.length, todo: res.data.filter((e) => !e.attempts).length, done: res.data.filter((e) => e.attempts).length, ai: res.data.filter((e) => e.source === 'ai').length }
    : null;
  const next = res.status === 'ready' ? pickNext(res.data) : null;

  return (
    <div className="min-h-[calc(100dvh-var(--student-header-height))] bg-surface">
      <PageContainer className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:gap-6">
        <ExamsHeader exams={res.status === 'ready' ? res.data : null} />

        {res.status === 'loading' && (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
            <Skeleton className="h-80 rounded-3xl" />
            <Skeleton className="h-80 rounded-3xl" />
          </div>
        )}
        {next && res.status === 'ready' && (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] sm:gap-6">
            <NextExamCard pick={next} onStructure={() => setStructureOf(next.exam)} />
            <RecentExams
              exams={[...res.data].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).filter((e) => e.id !== next.exam.id).slice(0, 5)}
              onStructure={setStructureOf}
            />
          </div>
        )}

        <h2 className="sr-only">Tất cả đề</h2>
        <div className="flex flex-col gap-3 pt-2 lg:flex-row lg:items-center lg:justify-between">
          <div role="tablist" aria-label="Lọc đề" className="flex w-fit max-w-full gap-1 overflow-x-auto rounded-full bg-surface-muted p-1 [scrollbar-width:none]">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                role="tab"
                type="button"
                aria-selected={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'relative min-h-9 shrink-0 rounded-full px-3.5 text-label font-semibold whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                  filter === f.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {filter === f.id && <motion.span layoutId="exam-filter" className="absolute inset-0 rounded-full bg-background shadow-soft" />}
                <span className="relative">
                  {f.label}
                  {counts && <span className="ml-1.5 text-caption text-muted-foreground tabular-nums">{counts[f.id]}</span>}
                </span>
              </button>
            ))}
          </div>
          <label className="relative block lg:w-72">
            <span className="sr-only">Tìm đề theo tên hoặc chương</span>
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Tìm theo tên đề hoặc chương"
              className="h-10 w-full rounded-full border border-border bg-background pr-3 pl-9 text-label text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20"
            />
          </label>
        </div>

        {res.status === 'error' && <ErrorState onRetry={res.reload} />}
        {res.status === 'loading' && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-56 rounded-2xl" />
            ))}
          </div>
        )}
        {res.status === 'ready' &&
          (list.length === 0 ? (
            <EmptyState
              title={query ? 'Không thấy đề nào khớp' : 'Chưa có đề nào ở đây'}
              message={query ? 'Thử từ khoá khác, ví dụ tên chương.' : 'Nhắn cho Examind để tạo đề ôn đúng phần bạn cần.'}
              action={
                <Button href="/exams/new" leftIcon={<Plus aria-hidden="true" />}>
                  Tạo đề với AI
                </Button>
              }
            />
          ) : (
            <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {list.map((exam) => (
                <li key={exam.id}>
                  <ExamCard exam={exam} onStructure={() => setStructureOf(exam)} />
                </li>
              ))}
            </ul>
          ))}
      </PageContainer>
      <AnimatePresence>{structureOf && <ExamStructureDialog exam={structureOf} onClose={() => setStructureOf(null)} />}</AnimatePresence>
    </div>
  );
}

const scoreText = { success: 'text-success', primary: 'text-primary', warning: 'text-warning', danger: 'text-danger' } as const;

/**
 * Thẻ đề như một tờ phiếu: viền trên là tỉ lệ ba phần của đề, điểm cao nhất là con số lớn bên phải.
 * Bấm tên đề mở trang đề; nút "Cấu trúc" mở popup tổng quan.
 */
function ExamCard({ exam, onStructure }: { exam: ExamSummary; onStructure: () => void }) {
  const isNew = exam.attempts === 0 && !exam.hasActiveAttempt;
  const parts = exam.sections.map((s) => ({ type: s.type, n: s.questionIds.length })).filter((p) => p.n > 0);
  const chapterNames = exam.chapters.map((c) => chapterOf(c).name);

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-2xl bg-background shadow-soft transition-shadow duration-300 hover:shadow-lift">
      <div className="flex h-1.5" aria-hidden="true">
        {parts.map((p) => (
          <span key={p.type} className={typeColor[p.type]} style={{ width: `${(p.n / exam.questionCount) * 100}%` }} />
        ))}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
          <div className="grid gap-1">
            <h2 className="text-body-lg leading-snug font-semibold text-foreground">
              <Link
                href={`/exams/${exam.id}`}
                className="line-clamp-2 rounded-sm transition-colors after:absolute after:inset-0 after:rounded-2xl group-hover:text-primary focus-visible:outline-none group-has-[a:focus-visible]:underline"
              >
                {exam.title}
              </Link>
            </h2>
            <p className="flex items-center gap-1.5 text-caption text-muted-foreground">
              {exam.source === 'ai' ? <Sparkles className="size-3.5 text-accent-strong" aria-hidden="true" /> : <Library className="size-3.5" aria-hidden="true" />}
              {exam.source === 'ai' ? 'Tạo với AI' : 'Từ ngân hàng'} · {relativeDay(exam.createdAt)}
            </p>
          </div>
          {exam.bestScore !== null ? (
            <p className="grid justify-items-end leading-none">
              <span className={cn('text-[2rem] font-bold tracking-tight tabular-nums', scoreText[scoreTone(exam.bestScore)])}>{formatScore(exam.bestScore)}</span>
              <span className="mt-1 text-[0.6875rem] whitespace-nowrap text-muted-foreground">điểm cao nhất</span>
            </p>
          ) : (
            <span className="rounded-full bg-accent-subtle px-2.5 py-1 text-caption font-semibold whitespace-nowrap text-accent-strong">{exam.hasActiveAttempt ? 'Đang làm' : 'Chưa làm'}</span>
          )}
        </div>

        <p className="line-clamp-1 text-caption text-muted-foreground" title={chapterNames.join(' · ')}>
          {chapterNames.join(' · ')}
        </p>

        <p className="flex flex-wrap gap-x-3 gap-y-1 text-caption text-muted-foreground tabular-nums">
          <span><b className="font-semibold text-foreground">{exam.questionCount}</b> câu</span>
          <span>{examDuration(exam.durationMinutes)}</span>
          {exam.attempts > 0 && exam.lastAttemptAt && (
            <span>{exam.attempts} lượt · gần nhất {relativeDay(exam.lastAttemptAt).toLowerCase()}</span>
          )}
        </p>

        <div className="relative z-10 mt-auto flex items-center justify-between gap-2 border-t border-border pt-3">
          <button
            type="button"
            onClick={onStructure}
            className="-ml-2 inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2 text-label font-semibold text-muted-foreground transition-colors hover:bg-surface hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
          >
            <ListTree className="size-4" aria-hidden="true" /> Cấu trúc
          </button>
          <Button size="sm" variant={isNew || exam.hasActiveAttempt ? 'primary' : 'secondary'} href={`/exams/${exam.id}/take`} leftIcon={<Play aria-hidden="true" />}>
            {exam.hasActiveAttempt ? 'Làm tiếp' : isNew ? 'Làm bài' : 'Làm lại'}
          </Button>
        </div>
      </div>
    </article>
  );
}
