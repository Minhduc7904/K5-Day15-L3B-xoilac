'use client';

import { ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { Skeleton } from '@/components/ui/feedback';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppSelector } from '@/store';
import { studyApi } from '../api';
import { ErrorState, PageContainer } from '../components/page-states';
import { ScoreBadge } from '../components/score-badge';
import { formatDuration, relativeDay } from '../format';
import type { DashboardData } from '../types';
import { useResource } from '../use-resource';
import { ChapterStats } from './chapter-stats';
import { ScoreChart } from './score-chart';
import { StudyHero } from './study-hero';
import { StudyRadar } from './study-radar';

const linkStyle = 'rounded-sm text-label font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring';

export function DashboardPage() {
  const res = useResource(() => studyApi.getDashboard(), 'dashboard');
  const user = useAppSelector((state) => state.auth.user);
  const hydrated = useHydrated();
  const name = (hydrated ? user?.display_name?.trim() : null) || 'bạn';

  return (
    <div className="min-h-[calc(100dvh-var(--student-header-height))] bg-surface">
      <PageContainer className="grid gap-5 sm:gap-6">
        {res.status === 'loading' && <DashboardSkeleton />}
        {res.status === 'error' && <ErrorState onRetry={res.reload} />}
        {res.status === 'ready' && <DashboardBody name={name} data={res.data} />}
      </PageContainer>
    </div>
  );
}

function DashboardBody({ name, data }: { name: string; data: DashboardData }) {
  return (
    <>
      <StudyHero name={name} data={data} />
      <div className="grid gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <ScoreChart scores={data.scores} />
        <StudyRadar recent={data.recent} days={data.streak.days} />
      </div>
      <div className="grid items-start gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <ChapterStats chapters={data.chapters} />
        <RecentAttempts recent={data.recent} />
      </div>
    </>
  );
}

function RecentAttempts({ recent }: { recent: DashboardData['recent'] }) {
  return (
    <section aria-labelledby="recent-title" className="min-w-0 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 id="recent-title" className="text-h3 text-foreground">Làm gần đây</h2>
        <Link href="/exams" className={linkStyle}>Xem tất cả</Link>
      </div>
      {recent.length === 0 ? (
        <p className="py-6 text-label text-muted-foreground">Các đề đã nộp sẽ xuất hiện ở đây.</p>
      ) : (
        <ol className="grid gap-1">
          {recent.map(({ attempt, exam }) => (
            <li key={attempt.id}>
              <Link
                href={`/results/${attempt.id}`}
                className="group -mx-2 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <ScoreBadge score={attempt.score} />
                <span className="grid min-w-0 gap-0.5">
                  <span className="line-clamp-2 text-label font-semibold text-foreground group-hover:text-primary">{exam.title}</span>
                  <span className="text-caption text-muted-foreground">
                    <time dateTime={attempt.submittedAt}>{relativeDay(attempt.submittedAt)}</time> · {attempt.correct}/{attempt.total} câu · {formatDuration(attempt.durationSeconds)}
                  </span>
                </span>
                <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-6" aria-busy="true" aria-label="Đang tải tổng quan">
      <Skeleton className="h-96 rounded-3xl lg:h-80" />
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Skeleton className="h-80 rounded-2xl" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
    </div>
  );
}
