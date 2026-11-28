'use client';

import { Gauge, Hourglass, Sigma, Timer, Zap } from 'lucide-react';
import { motion } from 'motion/react';
import { Bar, BarChart, CartesianGrid, Cell, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipContentProps } from 'recharts';
import { cn } from '@/lib/cn';
import { chapterOf } from '../chapters';
import { difficultyLabels, typeLabels } from '../labels';
import type { QuestionResult } from '../grading';
import type { Attempt, Exam } from '../types';

/** Số giây dạng m:ss (vd 1:05). */
export const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

const ROMAN = ['I', 'II', 'III', 'IV'];
type Status = QuestionResult['status'];
export const statusMeta: Record<Status, { label: string; fill: string; text: string; dot: string }> = {
  correct: { label: 'Đúng', fill: 'var(--color-success)', text: 'text-success', dot: 'bg-success' },
  partial: { label: 'Đúng một phần', fill: 'var(--color-info)', text: 'text-info', dot: 'bg-info' },
  wrong: { label: 'Sai', fill: 'var(--color-danger)', text: 'text-danger', dot: 'bg-danger' },
  skipped: { label: 'Bỏ trống', fill: 'var(--color-input)', text: 'text-muted-foreground', dot: 'bg-input' },
};
const tick = { fill: 'var(--color-muted-foreground)', fontSize: 11 };
const ease = [0.16, 1, 0.3, 1] as const;

interface Row {
  n: number;
  id: string;
  part: number;
  seconds: number;
  status: Status;
  result: QuestionResult;
}

/**
 * Nhịp độ làm bài: thời gian mở từng câu (cột, tô màu theo kết quả), đường trung bình,
 * nền chia theo phần, và các nhận xét rút ra từ chính số liệu đó.
 */
export function PaceSection({ attempt, exam, results, onJump }: { attempt: Attempt; exam: Exam; results: QuestionResult[]; onJump: (id: string) => void }) {
  const times = attempt.questionSeconds;

  if (!times || Object.keys(times).length === 0) {
    return (
      <section aria-labelledby="pace-title" className="rounded-2xl bg-background p-5 shadow-soft sm:p-6">
        <h2 id="pace-title" className="text-h3 text-foreground">Nhịp độ làm bài</h2>
        <p className="mt-2 max-w-prose text-label text-muted-foreground">
          Lượt này được nộp trước khi Examind ghi thời gian từng câu, nên chưa vẽ được nhịp độ. Làm lại đề để xem bạn dừng lâu ở câu nào nhé.
        </p>
      </section>
    );
  }

  // Ghép kết quả với phần và thời gian.
  const partOf = new Map<string, number>();
  exam.sections.forEach((s, i) => s.questionIds.forEach((id) => partOf.set(id, i)));
  const rows: Row[] = results.map((r, i) => ({ n: i + 1, id: r.question.id, part: partOf.get(r.question.id) ?? 0, seconds: times[r.question.id] ?? 0, status: r.status, result: r }));
  const total = rows.reduce((a, r) => a + r.seconds, 0);
  const avg = total / rows.length;
  const opened = rows.filter((r) => r.seconds > 0);
  const slowest = [...rows].sort((a, b) => b.seconds - a.seconds);
  const fastest = opened.length ? [...opened].sort((a, b) => a.seconds - b.seconds)[0] : null;
  const parts = exam.sections.map((s, i) => {
    const rs = rows.filter((r) => r.part === i);
    return { i, type: s.type, rs, seconds: rs.reduce((a, r) => a + r.seconds, 0), first: rs[0]?.n ?? 0, last: rs.at(-1)?.n ?? 0 };
  }).filter((p) => p.rs.length);

  const avgBy = (filter: (r: Row) => boolean) => {
    const rs = rows.filter(filter);
    return rs.length ? rs.reduce((a, r) => a + r.seconds, 0) / rs.length : null;
  };
  const avgRight = avgBy((r) => r.status === 'correct');
  const avgMissed = avgBy((r) => r.status === 'wrong' || r.status === 'partial');
  const top = slowest.slice(0, 3).filter((r) => r.seconds > 0);
  const insight = makeInsight(top, avgRight, avgMissed, parts, total);

  return (
    <section aria-labelledby="pace-title" className="grid gap-5 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="pace-title" className="text-h3 text-foreground">Nhịp độ làm bài</h2>
          <p className="text-caption text-muted-foreground">Thời gian bạn mở từng câu, cộng cả các lần quay lại. Bấm vào cột để xem lại câu đó.</p>
        </div>
        <ul className="flex flex-wrap gap-x-3 gap-y-1" aria-label="Chú thích màu">
          {(Object.keys(statusMeta) as Status[]).map((s) => (
            <li key={s} className="flex items-center gap-1.5 text-caption text-muted-foreground">
              <i className={cn('size-2.5 rounded-sm', statusMeta[s].dot)} aria-hidden="true" />
              {statusMeta[s].label}
            </li>
          ))}
        </ul>
      </div>

      <dl className="grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4">
        <Stat Icon={Sigma} label="Tổng thời gian" value={mmss(total)} note={exam.durationMinutes > 0 ? `trên ${exam.durationMinutes} phút cho phép` : 'không giới hạn giờ'} />
        <Stat Icon={Gauge} label="Trung bình mỗi câu" value={mmss(avg)} note={`${rows.length} câu`} />
        <Stat Icon={Hourglass} label="Lâu nhất" value={slowest[0] ? mmss(slowest[0].seconds) : '–'} note={slowest[0] ? `Câu ${slowest[0].n} · ${statusMeta[slowest[0].status].label.toLowerCase()}` : undefined} tone={slowest[0] && statusMeta[slowest[0].status].text} onClick={slowest[0] ? () => onJump(slowest[0].id) : undefined} />
        <Stat Icon={Zap} label="Nhanh nhất" value={fastest ? mmss(fastest.seconds) : '–'} note={fastest ? `Câu ${fastest.n} · ${statusMeta[fastest.status].label.toLowerCase()}` : undefined} tone={fastest ? statusMeta[fastest.status].text : undefined} onClick={fastest ? () => onJump(fastest.id) : undefined} />
      </dl>

      {/* Biểu đồ thời gian từng câu */}
      <div className="-mx-1 overflow-x-auto pb-1 [scrollbar-width:thin]">
        <div className="h-64 sm:h-72" style={{ minWidth: Math.max(480, rows.length * 22) }} role="img" aria-label={`Biểu đồ thời gian ${rows.length} câu. Trung bình ${mmss(avg)} mỗi câu, lâu nhất câu ${slowest[0]?.n} ${mmss(slowest[0]?.seconds ?? 0)}.`}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={rows} margin={{ top: 22, right: 8, bottom: 0, left: -8 }} barCategoryGap="18%">
              {parts.map((p) => (
                <ReferenceArea
                  key={p.i}
                  x1={p.first}
                  x2={p.last}
                  fill={p.i % 2 ? 'var(--color-surface)' : 'transparent'}
                  fillOpacity={1}
                  ifOverflow="extendDomain"
                  label={{ value: `Phần ${ROMAN[p.i]}`, position: 'insideTop', dy: -20, fill: 'var(--color-muted-foreground)', fontSize: 11, fontWeight: 600 }}
                />
              ))}
              <CartesianGrid vertical={false} stroke="var(--color-border)" />
              <XAxis dataKey="n" tick={tick} tickLine={false} axisLine={{ stroke: 'var(--color-border)' }} interval={rows.length > 24 ? 1 : 0} />
              <YAxis tick={tick} tickLine={false} axisLine={false} width={44} tickFormatter={(v: number) => mmss(v)} allowDecimals={false} />
              <ReferenceLine y={avg} stroke="var(--color-foreground)" strokeOpacity={0.5} strokeDasharray="4 4" label={{ value: `TB ${mmss(avg)}`, position: 'insideBottomLeft', fill: 'var(--color-foreground)', fontSize: 11, fontWeight: 600, dy: -2 }} />
              <Tooltip content={PaceTooltip} cursor={{ fill: 'var(--color-primary)', fillOpacity: 0.06 }} isAnimationActive={false} />
              <Bar dataKey="seconds" radius={[5, 5, 0, 0]} maxBarSize={28} onClick={(d) => onJump((d as unknown as Row).id)} className="cursor-pointer" animationDuration={700}>
                {rows.map((r) => (
                  <Cell key={r.id} fill={statusMeta[r.status].fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        {/* Thời gian theo phần */}
        <div className="grid content-start gap-3 rounded-xl bg-surface p-4">
          <h3 className="text-label font-semibold text-foreground">Thời gian chia theo phần</h3>
          <div className="flex h-3 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
            {parts.map((p, k) => (
              <motion.span
                key={p.i}
                className={cn('first:rounded-l-full last:rounded-r-full', ['bg-primary', 'bg-accent', 'bg-ember'][p.i] ?? 'bg-primary')}
                initial={{ width: 0 }}
                animate={{ width: `${(p.seconds / Math.max(1, total)) * 100}%` }}
                transition={{ delay: 0.2 + k * 0.08, duration: 0.7, ease }}
              />
            ))}
          </div>
          <ul className="grid gap-2">
            {parts.map((p) => {
              const right = p.rs.filter((r) => r.status === 'correct').length;
              return (
                <li key={p.i} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-3 text-label">
                  <span className="flex min-w-0 items-center gap-2">
                    <i className={cn('size-2.5 shrink-0 rounded-full', ['bg-primary', 'bg-accent', 'bg-ember'][p.i] ?? 'bg-primary')} aria-hidden="true" />
                    <span className="truncate text-foreground">Phần {ROMAN[p.i]} · {typeLabels[p.type]}</span>
                  </span>
                  <span className="text-caption text-muted-foreground tabular-nums">
                    <b className="text-label font-semibold text-foreground">{mmss(p.seconds)}</b> · {Math.round((p.seconds / Math.max(1, total)) * 100)}% · đúng {right}/{p.rs.length}
                  </span>
                </li>
              );
            })}
          </ul>
          {avgRight !== null && avgMissed !== null && (
            <p className="border-t border-border pt-3 text-caption text-muted-foreground">
              Trung bình câu <b className="text-success">đúng</b> {mmss(avgRight)}, câu <b className="text-danger">sai hoặc đúng một phần</b> {mmss(avgMissed)}.
            </p>
          )}
        </div>

        {/* Câu tốn thời gian nhất */}
        <div className="grid content-start gap-3">
          <h3 className="text-label font-semibold text-foreground">Ba câu bạn dừng lâu nhất</h3>
          <ol className="grid gap-2">
            {top.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => onJump(r.id)}
                  className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-border px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="flex size-8 items-center justify-center rounded-lg bg-foreground text-caption font-bold text-background tabular-nums">{r.n}</span>
                  <span className="grid min-w-0">
                    <span className={cn('text-caption font-semibold', statusMeta[r.status].text)}>{statusMeta[r.status].label}</span>
                    <span className="truncate text-caption text-muted-foreground">{difficultyLabels[r.result.question.difficulty]} · {chapterOf(r.result.question.chapter).name}</span>
                  </span>
                  <span className="text-body font-bold text-foreground tabular-nums">{mmss(r.seconds)}</span>
                </button>
              </li>
            ))}
          </ol>
          {insight && <p className="rounded-xl bg-accent-subtle px-3 py-2.5 text-label text-foreground">{insight}</p>}
        </div>
      </div>
    </section>
  );
}

function makeInsight(top: Row[], avgRight: number | null, avgMissed: number | null, parts: Array<{ i: number; seconds: number; rs: Row[] }>, total: number) {
  const missedTop = top.filter((r) => r.status === 'wrong' || r.status === 'partial' || r.status === 'skipped');
  if (missedTop.length >= 2) {
    const ch = chapterOf(missedTop[0].result.question.chapter).name;
    return `${missedTop.length}/${top.length} câu bạn dừng lâu nhất vẫn chưa đúng. Nghĩ lâu mà chưa ra thường là do chưa chắc cách làm, xem kỹ lời giải và ôn lại ${ch} nhé.`;
  }
  if (avgRight !== null && avgMissed !== null && avgMissed < avgRight * 0.7) {
    return 'Câu sai của bạn làm nhanh hơn hẳn câu đúng. Có thể bạn đang vội ở những câu này, lần sau đọc kỹ đề thêm một chút.';
  }
  const heavy = [...parts].sort((a, b) => b.seconds - a.seconds)[0];
  if (heavy && total > 0 && heavy.seconds / total > 0.5 && parts.length > 1) {
    return `Phần ${ROMAN[heavy.i]} chiếm hơn nửa thời gian làm bài. Khi thi thật, nhớ chừa giờ cho các phần còn lại.`;
  }
  return 'Nhịp độ khá đều. Giữ phong độ này nhé!';
}

function Stat({ Icon, label, value, note, tone, onClick }: { Icon: typeof Timer; label: string; value: string; note?: string; tone?: string; onClick?: () => void }) {
  const body = (
    <>
      <dt className="flex items-center gap-1.5 text-caption text-muted-foreground">
        <Icon className="size-3.5" aria-hidden="true" /> {label}
      </dt>
      <dd className="text-h2 leading-tight font-bold text-foreground tabular-nums">{value}</dd>
      {note && <dd className={cn('truncate text-caption', tone ?? 'text-muted-foreground')}>{note}</dd>}
    </>
  );
  return onClick ? (
    <button type="button" onClick={onClick} className="grid content-start rounded-xl bg-surface p-3 text-left transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-ring sm:p-4">
      {body}
    </button>
  ) : (
    <div className="grid content-start rounded-xl bg-surface p-3 sm:p-4">{body}</div>
  );
}

function PaceTooltip({ active, payload }: Pick<TooltipContentProps<number, string>, 'active' | 'payload'>) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload as Row;
  const q = r.result.question;
  return (
    <div className="grid max-w-60 gap-0.5 rounded-xl bg-foreground px-3 py-2 text-caption text-background shadow-lift">
      <p className="font-semibold">
        Câu {r.n} · Phần {ROMAN[r.part]} · <span className="tabular-nums">{mmss(r.seconds)}</span>
      </p>
      <p className="opacity-80">{statusMeta[r.status].label} · {difficultyLabels[q.difficulty]}</p>
      <p className="truncate opacity-70">{chapterOf(q.chapter).name}</p>
    </div>
  );
}
