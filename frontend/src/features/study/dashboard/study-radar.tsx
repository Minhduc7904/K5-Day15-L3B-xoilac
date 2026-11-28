'use client';

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, type TooltipContentProps } from 'recharts';
import type { DashboardData } from '../types';

type Props = { recent: DashboardData['recent']; days: DashboardData['streak']['days'] };
type Metric = { label: string; axis: string; value: number | null; plot: number; detail: string };

function toPercent(value: number, total: number) {
  return total > 0 ? Math.round(Math.min(value / total, 1) * 100) : null;
}

function getMetrics({ recent, days }: Props): Metric[] {
  let total = 0;
  let answered = 0;
  let correct = 0;
  let seconds = 0;
  let timedAnswers = 0;
  let expectedSeconds = 0;
  let reachedTarget = 0;

  for (const { attempt, exam } of recent) {
    const answeredInExam = attempt.answered ?? 0;
    total += attempt.total;
    answered += answeredInExam;
    correct += attempt.correct;
    if (attempt.total > 0 && answeredInExam > 0 && attempt.durationSeconds > 0 && exam.durationMinutes > 0) {
      timedAnswers += answeredInExam;
      seconds += attempt.durationSeconds;
      expectedSeconds += exam.durationMinutes * 60 * (answeredInExam / attempt.total);
    }
    if (attempt.score >= 8) reachedTarget++;
  }

  const activity = days.slice(-7);
  const activeDays = activity.filter(({ studied }) => studied).length;
  const metrics = [
    { label: 'Độ chính xác', axis: 'Chính xác', value: toPercent(correct, answered), detail: `${correct}/${answered} câu đã trả lời được chấm đúng` },
    { label: 'Tốc độ làm bài', axis: 'Tốc độ', value: toPercent(expectedSeconds, seconds), detail: timedAnswers > 0 ? `Trung bình ${Math.round(seconds / timedAnswers)} giây/câu, đối chiếu thời lượng đề` : 'Chưa có bài làm đủ dữ liệu thời gian' },
    { label: 'Hoàn thành bài', axis: 'Hoàn thành', value: toPercent(answered, total), detail: `${answered}/${total} câu có câu trả lời` },
    { label: 'Nhịp học', axis: 'Nhịp học', value: toPercent(activeDays, activity.length), detail: `${activeDays}/${activity.length} ngày gần nhất có học` },
    { label: 'Đạt mục tiêu', axis: 'Mục tiêu', value: toPercent(reachedTarget, recent.length), detail: `${reachedTarget}/${recent.length} lượt đạt từ 8 điểm` },
  ];
  return metrics.map((metric) => ({ ...metric, plot: metric.value ?? 0 }));
}

export function StudyRadar({ recent, days }: Props) {
  const metrics = getMetrics({ recent, days });
  const byAxis = new Map(metrics.map((metric) => [metric.axis, metric]));
  const scored = metrics.filter((metric) => metric.value !== null);
  const weakest = scored.length ? scored.reduce((low, metric) => (metric.plot < low.plot ? metric : low)) : null;

  return (
    <section aria-labelledby="study-radar-title" className="grid content-start gap-2 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <div>
        <h2 id="study-radar-title" className="text-h3 text-foreground">Hồ sơ học tập</h2>
        <p className="mt-0.5 text-caption text-muted-foreground">Rê chuột hoặc chạm vào từng góc để xem chi tiết.</p>
      </div>
      {recent.length === 0 ? (
        <p className="py-8 text-label text-muted-foreground">Nộp một đề để xem hồ sơ học tập của bạn.</p>
      ) : (
        <>
          <div className="-mx-2 h-64 min-w-0 sm:h-72">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <RadarChart data={metrics} outerRadius="68%" margin={{ top: 14, right: 30, bottom: 6, left: 30 }}>
                <defs>
                  <radialGradient id="radar-fill">
                    <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0.4} />
                  </radialGradient>
                </defs>
                <PolarGrid gridType="polygon" stroke="var(--color-border)" />
                <PolarAngleAxis
                  dataKey="axis"
                  tickLine={false}
                  tick={({ x, y, payload, textAnchor }) => {
                    const metric = byAxis.get(String(payload.value));
                    return (
                      <text x={x} y={y} textAnchor={textAnchor} dominantBaseline="central" className="text-[11px]">
                        <tspan x={x} dy="-0.55em" fill="var(--color-muted-foreground)">{payload.value}</tspan>
                        <tspan x={x} dy="1.25em" fill="var(--color-foreground)" fontWeight={700} fontSize={13}>
                          {metric?.value === null || metric === undefined ? '—' : `${metric.value}%`}
                        </tspan>
                      </text>
                    );
                  }}
                />
                <PolarRadiusAxis domain={[0, 100]} ticks={[25, 50, 75, 100]} tick={false} axisLine={false} />
                <Tooltip content={RadarTooltip} cursor={false} isAnimationActive={false} />
                <Radar
                  dataKey="plot"
                  name="Kết quả của bạn"
                  stroke="var(--color-accent-strong)"
                  strokeWidth={2}
                  strokeLinejoin="round"
                  fill="url(#radar-fill)"
                  fillOpacity={1}
                  dot={{ r: 4, fill: 'var(--color-background)', stroke: 'var(--color-accent-strong)', strokeWidth: 2 }}
                  activeDot={{ r: 7, fill: 'var(--color-accent)', stroke: 'var(--color-background)', strokeWidth: 3 }}
                  animationDuration={900}
                  animationEasing="ease-out"
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          {weakest && (
            <p className="rounded-xl bg-accent-subtle px-3.5 py-2.5 text-caption text-foreground">
              Góc cần chăm thêm: <strong className="font-semibold">{weakest.label}</strong> ({weakest.value}%).
            </p>
          )}
          <dl className="sr-only">
            {metrics.map(({ label, value, detail }) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value === null ? 'Chưa có dữ liệu' : `${value}%`}, {detail}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </section>
  );
}

function RadarTooltip({ active, payload }: Pick<TooltipContentProps<number, string>, 'active' | 'payload'>) {
  const metric = payload[0]?.payload as Metric | undefined;
  if (!active || !metric) return null;
  return (
    <div className="grid max-w-56 gap-0.5 rounded-xl bg-foreground px-3.5 py-2.5 text-background shadow-lift">
      <p className="flex items-baseline justify-between gap-4 text-label font-semibold">
        {metric.label}
        <span className="text-body font-bold tabular-nums text-accent">{metric.value === null ? '—' : `${metric.value}%`}</span>
      </p>
      <p className="text-caption text-background/80">{metric.detail}</p>
    </div>
  );
}
