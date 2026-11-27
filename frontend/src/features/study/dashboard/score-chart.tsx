'use client';

import Link from 'next/link';
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, type DotItemDotProps, type TooltipContentProps } from 'recharts';
import { cn } from '@/lib/cn';
import { shortDate } from '../format';
import { formatScore } from '../grading';
import type { DashboardData } from '../types';

type Score = DashboardData['scores'][number];
const tickStyle = { fill: 'var(--color-muted-foreground)', fontSize: 11 };

export function ScoreChart({ scores }: { scores: Score[] }) {
  const latest = scores.at(-1);
  const previous = scores.at(-2);
  const delta = latest && previous ? Math.round((latest.score - previous.score) * 100) / 100 : null;
  const datesByAttempt = new Map(scores.map(({ attemptId, date }) => [attemptId, shortDate(date)]));

  return (
    <section aria-labelledby="chart-title" className="min-w-0 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <div>
          <h2 id="chart-title" className="text-h3 text-foreground">Điểm qua các đề</h2>
          <p className="mt-1 text-caption text-muted-foreground">Điểm luyện tập trên thang 10</p>
        </div>
        {latest && <Link href={`/results/${latest.attemptId}`} className="rounded-sm text-caption font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">Xem lượt mới nhất</Link>}
      </div>
      {latest ? (
        <>
          <div className="mt-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <p className="flex items-baseline gap-1 text-caption text-muted-foreground">
              <strong className="text-3xl leading-none font-semibold tracking-tight tabular-nums text-foreground">{formatScore(latest.score)}</strong>
              điểm gần nhất
            </p>
            {delta !== null && (
              <p className={cn('text-caption font-medium tabular-nums', delta === 0 ? 'text-muted-foreground' : delta > 0 ? 'text-success' : 'text-danger')}>
                {delta === 0 ? 'Bằng lượt trước' : `${delta > 0 ? '+' : ''}${formatScore(delta)} so với lượt trước`}
              </p>
            )}
          </div>
          <div className="mt-3 h-56 min-w-0 sm:h-64">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <AreaChart data={scores} margin={{ top: 12, right: 19, bottom: 0, left: 0 }} accessibilityLayer>
                <defs>
                  <linearGradient id="score-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--color-border)" />
                <XAxis
                  dataKey="attemptId"
                  axisLine={false}
                  tickLine={false}
                  tick={tickStyle}
                  tickMargin={9}
                  minTickGap={20}
                  padding={{ left: 12, right: 12 }}
                  tickFormatter={(attemptId) => datesByAttempt.get(attemptId) ?? ''}
                />
                <YAxis type="number" domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} width={24} tickMargin={5} tickLine={false} axisLine={false} tick={tickStyle} />
                <ReferenceLine y={8} stroke="var(--color-accent-strong)" strokeDasharray="3 5" />
                <Tooltip content={ScoreTooltip} cursor={{ stroke: 'var(--color-input)', strokeDasharray: '3 4' }} isAnimationActive={false} />
                <Area
                  type="monotoneX"
                  dataKey="score"
                  stroke="var(--color-primary)"
                  strokeWidth={2.5}
                  fill="url(#score-fill)"
                  dot={({ cx, cy, payload }) => <ScorePoint cx={cx} cy={cy} payload={payload} last={latest.attemptId} />}
                  activeDot={false}
                  animationDuration={900}
                  animationEasing="ease-out"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="ml-6 flex items-center gap-2 text-caption text-muted-foreground">
            <span className="w-5 border-t border-dashed border-accent-strong" aria-hidden="true" />
            Mục tiêu 8 điểm
          </p>
        </>
      ) : (
        <p className="mt-4 border-t border-border py-5 text-label text-muted-foreground">Nộp đề đầu tiên để bắt đầu theo dõi điểm.</p>
      )}
    </section>
  );
}

function ScorePoint({ cx, cy, payload, last }: Pick<DotItemDotProps, 'cx' | 'cy'> & { payload?: Score; last: string }) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const isLatest = payload.attemptId === last;
  return (
    <Link
      href={`/results/${payload.attemptId}`}
      prefetch={false}
      aria-label={`${payload.title}, ${shortDate(payload.date)}, ${formatScore(payload.score)} điểm. Xem kết quả.`}
      className="group outline-none"
    >
      <circle cx={cx} cy={cy} r={14} fill="transparent" />
      <circle cx={cx} cy={cy} r={9} fill="none" stroke="var(--color-ring)" strokeWidth={2} className="opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100" />
      <circle cx={cx} cy={cy} r={isLatest ? 5 : 3.75} fill={isLatest ? 'var(--color-primary)' : 'var(--color-background)'} stroke="var(--color-primary)" strokeWidth={2} aria-hidden="true" />
    </Link>
  );
}

function ScoreTooltip({ active, payload }: Pick<TooltipContentProps<number, string>, 'active' | 'payload'>) {
  const score = payload[0]?.payload as Score | undefined;
  if (!active || !score) return null;
  return (
    <div className="grid max-w-45 gap-0.5 rounded-lg bg-foreground px-3 py-2 text-background">
      <p className="text-caption text-background/80">{shortDate(score.date)}</p>
      <p className="line-clamp-2 text-caption">{score.title}</p>
      <p className="text-label font-semibold tabular-nums">{formatScore(score.score)} điểm</p>
    </div>
  );
}

