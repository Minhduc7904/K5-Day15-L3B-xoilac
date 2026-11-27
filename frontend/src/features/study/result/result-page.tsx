'use client';

import { BookOpen, Check, ChevronDown, Clock3, LayoutDashboard, Minus, RotateCcw, Sparkles, Timer, TrendingDown, TrendingUp, X } from 'lucide-react';
import { animate, AnimatePresence, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { studyApi } from '../api';
import { ErrorState, PageContainer } from '../components/page-states';
import { QuestionContent } from '../components/question-content';
import { chapterOf, difficultyLabels, typeLabels } from '../fixtures/chapters';
import { accuracyTone, formatDuration, longDate, percent, scoreTone } from '../format';
import { formatScore, type QuestionResult } from '../grading';
import { useResource } from '../use-resource';
import { mmss, PaceSection, statusMeta } from './pace';

type Data = Awaited<ReturnType<typeof studyApi.getResult>>;

export function ResultPage({ attemptId }: { attemptId: string }) {
  const res = useResource(() => studyApi.getResult(attemptId), `result-${attemptId}`);
  return (
    <div className="min-h-[calc(100dvh-var(--student-header-height))] bg-surface">
    <PageContainer className="grid grid-cols-[minmax(0,1fr)] gap-6">
      {res.status === 'loading' && (
        <div className="grid gap-6" aria-busy="true">
          <Skeleton className="h-72 rounded-3xl" />
          <Skeleton className="h-96 rounded-3xl" />
        </div>
      )}
      {res.status === 'error' && (
        <ErrorState title={res.error.name === 'NotFoundError' ? 'Không tìm thấy kết quả này' : undefined} onRetry={res.error.name === 'NotFoundError' ? undefined : res.reload} />
      )}
      {res.status === 'ready' && <Result data={res.data} />}
    </PageContainer>
    </div>
  );
}

const ringColor = { success: 'stroke-success', primary: 'stroke-accent', warning: 'stroke-warning', danger: 'stroke-flame' } as const;
const ease = [0.16, 1, 0.3, 1] as const;

function ScoreRing({ score }: { score: number }) {
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => formatScore(Math.round(v * 100) / 100));
  const dash = useTransform(mv, (v) => `${(v / 10) * 2 * Math.PI * 70} ${2 * Math.PI * 70}`);
  useEffect(() => {
    const c = animate(mv, score, { duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.2 });
    return () => c.stop();
  }, [mv, score]);
  return (
    <div className="relative size-40 shrink-0 sm:size-44" role="img" aria-label={`${formatScore(score)} trên 10 điểm`}>
      <svg viewBox="0 0 160 160" className="size-full -rotate-90" aria-hidden="true">
        <circle cx="80" cy="80" r="70" className="fill-none stroke-primary-foreground/12" strokeWidth="12" />
        <motion.circle cx="80" cy="80" r="70" className={cn('fill-none', ringColor[scoreTone(score)])} strokeWidth="12" strokeLinecap="round" style={{ strokeDasharray: dash }} />
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center" aria-hidden="true">
        <motion.span className="text-[2.75rem] leading-none font-bold tabular-nums">{text}</motion.span>
        <span className="text-caption text-primary-foreground/70">trên 10 điểm</span>
      </div>
    </div>
  );
}

function headline(score: number) {
  if (score >= 9) return { title: 'Xuất sắc!', text: 'Bạn nắm phần này rất chắc. Thử đề khó hơn nhé!' };
  if (score >= 8) return { title: 'Làm tốt lắm!', text: 'Chỉ còn vài chỗ nhỏ, xem lại lời giải là ổn.' };
  if (score >= 6.5) return { title: 'Khá ổn rồi đó!', text: 'Ôn thêm phần sai là điểm sẽ lên nhanh.' };
  if (score >= 5) return { title: 'Cố thêm chút nữa nhé', text: 'Xem lời giải từng câu sai, rồi làm một đề ôn đúng phần đó.' };
  return { title: 'Đừng nản nhé!', text: 'Ai cũng có lúc vấp. Xem lời giải, rồi để Examind ra đề ôn phần này cho bạn.' };
}

type FilterId = (typeof FILTERS)[number]['id'];

function Result({ data }: { data: Data }) {
  const { attempt, exam, graded, previous } = data;
  const reduce = useReducedMotion();
  const [filter, setFilter] = useState<FilterId>('all');
  const delta = previous ? Math.round((attempt.score - previous.score) * 100) / 100 : null;
  const h = headline(attempt.score);
  const counts = (['correct', 'partial', 'wrong', 'skipped'] as const).map((k) => ({ k, n: graded.results.filter((r) => r.status === k).length }));

  const chapters = useMemo(() => {
    const map = new Map<string, { correct: number; total: number }>();
    for (const r of graded.results) {
      const e = map.get(r.question.chapter) ?? { correct: 0, total: 0 };
      e.total += 1;
      if (r.status === 'correct') e.correct += 1;
      map.set(r.question.chapter, e);
    }
    return [...map.entries()].map(([code, v]) => ({ code, ...v })).sort((a, b) => a.correct / a.total - b.correct / b.total);
  }, [graded]);
  const weakest = chapters[0] && chapters[0].correct < chapters[0].total ? chapterOf(chapters[0].code).name : null;

  let offset = 0;
  const sections = exam.sections.map((s) => {
    const results = graded.results.slice(offset, offset + s.questionIds.length);
    offset += s.questionIds.length;
    return { ...s, points: results.reduce((a, r) => a + r.points, 0), max: results.reduce((a, r) => a + r.max, 0) };
  });

  const jump = (id: string) => {
    setFilter('all');
    requestAnimationFrame(() => {
      const el = document.getElementById(`review-${id}`);
      el?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      el?.focus({ preventScroll: true });
    });
  };

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:gap-6">
      {/* Điểm */}
      <section aria-labelledby="result-title" className="relative isolate overflow-hidden rounded-3xl bg-primary text-primary-foreground shadow-lift">
        <div aria-hidden="true" className="bg-grid-inverse absolute inset-0 -z-10 [mask-image:linear-gradient(to_bottom,black,transparent_95%)]" />
        <div className="grid gap-6 p-5 sm:p-8 md:grid-cols-[auto_minmax(0,1fr)] md:items-center lg:grid-cols-[auto_minmax(0,1fr)_minmax(0,17rem)]">
          <div data-tour="result-score" className="justify-self-center">
            <ScoreRing score={attempt.score} />
          </div>
          <div className="grid gap-3 text-center md:text-left">
            <p className="text-label font-semibold text-primary-foreground/70">
              <Link href={`/exams/${exam.id}`} className="rounded-sm underline-offset-4 hover:text-primary-foreground hover:underline focus-visible:outline-2 focus-visible:outline-accent">
                {exam.title}
              </Link>
            </p>
            <h1 id="result-title" className="text-h1">{h.title}</h1>
            <div className="flex flex-wrap justify-center gap-2 md:justify-start">
              {delta !== null && (
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label font-semibold',
                    delta > 0 ? 'bg-success text-primary-foreground' : delta < 0 ? 'bg-flame-strong text-primary-foreground' : 'bg-primary-foreground/12',
                  )}
                >
                  {delta > 0 ? <TrendingUp className="size-4" aria-hidden="true" /> : delta < 0 ? <TrendingDown className="size-4" aria-hidden="true" /> : <Minus className="size-4" aria-hidden="true" />}
                  {delta > 0 ? '+' : ''}
                  {formatScore(delta)} so với lần trước
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-foreground/12 px-3 py-1 text-label">
                <Clock3 className="size-4" aria-hidden="true" /> {formatDuration(attempt.durationSeconds)}
              </span>
            </div>

            {/* Kết quả từng câu: một thanh chia theo trạng thái */}
            <div className="mt-1 grid gap-2">
              <div className="flex h-3 gap-0.5 overflow-hidden rounded-full bg-primary-foreground/12" aria-hidden="true">
                {counts
                  .filter((c) => c.n)
                  .map((c, i) => (
                    <motion.span
                      key={c.k}
                      className={cn('first:rounded-l-full last:rounded-r-full', c.k === 'skipped' ? 'bg-primary-foreground/35' : statusMeta[c.k].dot)}
                      initial={{ width: 0 }}
                      animate={{ width: `${(c.n / graded.results.length) * 100}%` }}
                      transition={{ delay: 0.4 + i * 0.08, duration: 0.7, ease }}
                    />
                  ))}
              </div>
              <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-label md:justify-start">
                {counts.map((c) => (
                  <li key={c.k} className="flex items-center gap-1.5 text-primary-foreground/80">
                    <i className={cn('size-2.5 rounded-full', c.k === 'skipped' ? 'bg-primary-foreground/35' : statusMeta[c.k].dot)} aria-hidden="true" />
                    {statusMeta[c.k].label} <b className="font-bold text-primary-foreground tabular-nums">{c.n}</b>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2 md:col-span-2 lg:col-span-1">
            <motion.p
              className="relative mb-5 rounded-2xl rounded-br-sm bg-background px-4 py-3 text-label text-foreground shadow-soft"
              initial={reduce ? false : { opacity: 0, scale: 0.94, x: 6 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.6, ease }}
              style={{ originX: 1, originY: 1 }}
            >
              <svg aria-hidden="true" viewBox="0 0 14 14" className="absolute -right-[11px] bottom-0 size-3.5 -scale-x-100 fill-background">
                <path d="M14 0v14H0C7 12 12 7 14 0z" />
              </svg>
              {h.text}
            </motion.p>
            <motion.div className="w-20 sm:w-24" initial={reduce ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.4, ease }}>
              <Image
                src={`/brand/mascot/static/${attempt.score >= 8 ? 'success' : 'studying'}.webp`}
                alt=""
                width={192}
                height={192}
                unoptimized
                className="pixelated h-auto w-full drop-shadow-[0_10px_14px_rgb(3_23_47/0.45)]"
              />
            </motion.div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-primary-foreground/12 px-5 py-4 sm:px-8">
          {weakest && (
            <Link
              href={`/exams/new?q=${encodeURIComponent(`Ôn chương ${weakest}`)}`}
              className="inline-flex h-11 items-center gap-2 rounded-xl bg-flame-strong px-5 text-label font-semibold text-primary-foreground transition-[background-color,transform] hover:bg-danger-hover active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <Sparkles className="size-4" aria-hidden="true" /> Tạo đề ôn phần sai
            </Link>
          )}
          <Button variant="inverse" href={`/exams/${exam.id}/take`} leftIcon={<RotateCcw aria-hidden="true" />}>
            Làm lại đề này
          </Button>
          <Button variant="inverse" href="/dashboard" leftIcon={<LayoutDashboard aria-hidden="true" />} className="border-transparent">
            Về tổng quan
          </Button>
          <p className="w-full text-caption text-primary-foreground/60 lg:ml-auto lg:w-auto">Nộp lúc {longDate(attempt.submittedAt)} · điểm luyện tập, không phải điểm chính thức</p>
        </div>
      </section>

      <PaceSection attempt={attempt} exam={exam} results={graded.results} onJump={jump} />

      {/* Phân tích */}
      <div className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:gap-6 lg:grid-cols-2">
        <section aria-labelledby="by-section" className="rounded-2xl bg-background p-5 shadow-soft sm:p-6">
          <h2 id="by-section" className="mb-4 text-h3 text-foreground">Điểm theo phần</h2>
          <ul className="grid gap-4">
            {sections.map((s, i) => {
              const ratio = s.max ? s.points / s.max : 0;
              return (
                <li key={s.id} className="grid gap-1.5">
                  <div className="flex justify-between gap-3 text-label">
                    <span className="font-semibold text-foreground">{s.title}</span>
                    <span className="text-muted-foreground tabular-nums">
                      <b className="text-foreground">{formatScore(Math.round(s.points * 100) / 100)}</b>/{formatScore(s.max)} điểm
                    </span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-surface-muted" aria-hidden="true">
                    <motion.div className="h-full rounded-full bg-primary" initial={{ width: 0 }} animate={{ width: `${ratio * 100}%` }} transition={{ delay: 0.3 + i * 0.1, duration: 0.8, ease }} />
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-4 text-caption text-muted-foreground">
            Cách tính như đề THPT 2025: trắc nghiệm 0,25 điểm/câu; đúng/sai 0,1 – 0,25 – 0,5 – 1 điểm theo số ý đúng; trả lời ngắn 0,5 điểm/câu, rồi quy về thang 10.
          </p>
        </section>

        <section aria-labelledby="by-chapter" className="rounded-2xl bg-background p-5 shadow-soft sm:p-6">
          <h2 id="by-chapter" className="mb-4 text-h3 text-foreground">Theo chương</h2>
          <ul className="grid gap-4">
            {chapters.map((c, i) => {
              const ratio = c.correct / c.total;
              const tone = accuracyTone(ratio);
              return (
                <li key={c.code} className="grid min-w-0 gap-1.5">
                  <div className="flex justify-between gap-3 text-label">
                    <span className="truncate font-semibold text-foreground">{chapterOf(c.code).name}</span>
                    <span className={cn('shrink-0 font-bold tabular-nums', { success: 'text-success', warning: 'text-warning', danger: 'text-danger' }[tone])}>
                      {c.correct}/{c.total} · {percent(ratio)}
                    </span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-surface-muted" aria-hidden="true">
                    <motion.div
                      className={cn('h-full rounded-full', { success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger' }[tone])}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(4, ratio * 100)}%` }}
                      transition={{ delay: 0.3 + i * 0.08, duration: 0.8, ease }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <Review results={graded.results} times={attempt.questionSeconds} filter={filter} onFilter={setFilter} />
    </div>
  );
}

/* ---------------- Xem lại từng câu ---------------- */

const FILTERS = [
  { id: 'all', label: 'Tất cả' },
  { id: 'wrong', label: 'Sai & bỏ trống' },
  { id: 'partial', label: 'Đúng một phần' },
  { id: 'correct', label: 'Đúng' },
] as const;

const statusStyle = {
  correct: { label: 'Đúng', cls: 'bg-success-subtle text-success', Icon: Check },
  partial: { label: 'Đúng một phần', cls: 'bg-info-subtle text-info', Icon: Minus },
  wrong: { label: 'Sai', cls: 'bg-danger-subtle text-danger', Icon: X },
  skipped: { label: 'Bỏ trống', cls: 'bg-surface-muted text-muted-foreground', Icon: Minus },
} as const;

function Review({ results, times, filter, onFilter: setFilter }: { results: QuestionResult[]; times?: Record<string, number>; filter: FilterId; onFilter: (f: FilterId) => void }) {
  const indexed = results.map((r, i) => ({ r, i }));
  const shown = indexed.filter(({ r }) =>
    filter === 'all' ? true : filter === 'wrong' ? r.status === 'wrong' || r.status === 'skipped' : r.status === filter,
  );

  return (
    <section aria-labelledby="review-title" className="grid gap-4">
      <div data-tour="result-review" className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="review-title" className="text-h2 text-foreground">Xem lại bài làm</h2>
          <p className="text-caption text-muted-foreground">So đáp án của bạn với đáp án đúng, mở lời giải từng câu.</p>
        </div>
        <div role="tablist" aria-label="Lọc câu" className="flex max-w-full gap-1 overflow-x-auto rounded-2xl bg-surface-muted p-1">
          {FILTERS.map((f) => {
            const n = f.id === 'all' ? results.length : results.filter((r) => (f.id === 'wrong' ? r.status === 'wrong' || r.status === 'skipped' : r.status === f.id)).length;
            return (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={cn('relative shrink-0 rounded-xl px-3 py-1.5 text-caption font-semibold whitespace-nowrap focus-visible:outline-2 focus-visible:outline-ring', filter === f.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground')}
              >
                {filter === f.id && <motion.span layoutId="review-filter" className="absolute inset-0 rounded-xl bg-background shadow-soft" />}
                <span className="relative">
                  {f.label} <span className="tabular-nums opacity-70">{n}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="rounded-3xl border-2 border-dashed border-border p-8 text-center text-body text-muted-foreground">Không có câu nào ở mục này. 🎯</p>
      ) : (
        <ol className="grid gap-4">
          <AnimatePresence initial={false} mode="popLayout">
            {shown.map(({ r, i }) => (
              <motion.li key={r.question.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <ReviewCard result={r} index={i} seconds={times?.[r.question.id]} />
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
    </section>
  );
}

function ReviewCard({ result, index, seconds }: { result: QuestionResult; index: number; seconds?: number }) {
  const { question: q, answer, status } = result;
  const [open, setOpen] = useState(status !== 'correct');
  const s = statusStyle[status];
  const panelId = `solution-${q.id}`;

  return (
    <article id={`review-${q.id}`} tabIndex={-1} className="grid scroll-mt-[calc(var(--student-header-height)+1rem)] gap-4 rounded-2xl bg-background p-5 shadow-soft outline-none focus-visible:ring-4 focus-visible:ring-ring/25 sm:p-6" aria-label={`Câu ${index + 1}: ${s.label}`}>
      <header className="flex flex-wrap items-center gap-2">
        <span className="rounded-xl bg-foreground px-2.5 py-1 text-caption font-bold text-background">Câu {index + 1}</span>
        <span className={cn('inline-flex items-center gap-1 rounded-xl px-2.5 py-1 text-caption font-bold', s.cls)}>
          <s.Icon className="size-3.5" aria-hidden="true" /> {s.label}
          {status === 'partial' && result.tfCorrect !== undefined && ` (${result.tfCorrect}/4 ý)`}
        </span>
        <span className="text-caption text-muted-foreground">
          {typeLabels[q.type]} · {difficultyLabels[q.difficulty]} · {chapterOf(q.chapter).name}
        </span>
        <span className="ml-auto flex items-center gap-3 text-caption font-semibold text-muted-foreground tabular-nums">
          {seconds !== undefined && (
            <span className="inline-flex items-center gap-1" title="Thời gian bạn mở câu này">
              <Timer className="size-3.5" aria-hidden="true" /> {mmss(seconds)}
            </span>
          )}
          <span>+{formatScore(result.points)}/{formatScore(result.max)} điểm</span>
        </span>
      </header>

      <QuestionContent source={q.content} />

      {q.type === 'SINGLE_CHOICE' && (
        <ul className="grid gap-2 sm:grid-cols-2">
          {q.statements.map((st) => {
            const picked = answer === st.label;
            return (
              <li
                key={st.label}
                className={cn(
                  'flex items-center gap-3 rounded-2xl border-2 p-3',
                  st.correct ? 'border-success bg-success-subtle' : picked ? 'border-danger bg-danger-subtle' : 'border-border',
                )}
              >
                <span className={cn('flex size-8 shrink-0 items-center justify-center rounded-lg text-label font-bold', st.correct ? 'bg-success text-primary-foreground' : picked ? 'bg-danger text-primary-foreground' : 'bg-surface-muted text-muted-foreground')}>
                  {st.correct ? <Check className="size-4" aria-hidden="true" /> : picked ? <X className="size-4" aria-hidden="true" /> : st.label}
                </span>
                <span className="min-w-0 flex-1 text-body text-foreground">
                  <QuestionContent source={st.content} inline />
                </span>
                {picked && <span className="shrink-0 text-caption font-semibold text-muted-foreground">Bạn chọn</span>}
                <span className="sr-only">{st.correct ? '(đáp án đúng)' : ''}</span>
              </li>
            );
          })}
        </ul>
      )}

      {q.type === 'TRUE_FALSE' && (
        <div className="overflow-x-auto rounded-2xl border border-border">
          <table className="w-full min-w-[480px] text-left text-body">
            <thead className="bg-surface text-caption text-muted-foreground">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Ý</th>
                <th scope="col" className="w-24 px-3 py-2 font-semibold">Bạn chọn</th>
                <th scope="col" className="w-24 px-3 py-2 font-semibold">Đáp án</th>
              </tr>
            </thead>
            <tbody>
              {q.statements.map((st, i) => {
                const pick = Array.isArray(answer) ? answer[i] : null;
                const ok = pick === st.correct;
                return (
                  <tr key={st.label} className="border-t border-border">
                    <td className="px-3 py-2.5">
                      <span className="flex gap-2">
                        <b className="text-primary">{st.label})</b>
                        <QuestionContent source={st.content} inline />
                      </span>
                    </td>
                    <td className={cn('px-3 py-2.5 font-semibold', pick === null || pick === undefined ? 'text-muted-foreground' : ok ? 'text-success' : 'text-danger')}>
                      {pick === null || pick === undefined ? '—' : pick ? 'Đúng' : 'Sai'}
                      {pick !== null && pick !== undefined && (ok ? ' ✓' : ' ✗')}
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-foreground">{st.correct ? 'Đúng' : 'Sai'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {q.type === 'SHORT_ANSWER' && (
        <div className="flex flex-wrap gap-3">
          <div className={cn('rounded-2xl border-2 px-4 py-2', status === 'correct' ? 'border-success bg-success-subtle' : status === 'skipped' ? 'border-border' : 'border-danger bg-danger-subtle')}>
            <p className="text-caption text-muted-foreground">Bạn trả lời</p>
            <p className="text-h3 font-bold text-foreground tabular-nums">{typeof answer === 'string' && answer ? answer : '—'}</p>
          </div>
          <div className="rounded-2xl border-2 border-success bg-success-subtle px-4 py-2">
            <p className="text-caption text-muted-foreground">Đáp án</p>
            <p className="text-h3 font-bold text-success tabular-nums">{q.answer}</p>
          </div>
        </div>
      )}

      {q.solution && (
        <div className="rounded-2xl bg-surface">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((o) => !o)}
            className="flex w-full items-center justify-between gap-3 rounded-2xl px-4 py-3 text-left text-label font-semibold text-primary focus-visible:outline-2 focus-visible:outline-ring"
          >
            <span className="inline-flex items-center gap-2">
              <BookOpen className="size-4" aria-hidden="true" /> Lời giải
            </span>
            <ChevronDown className={cn('size-5 transition-transform', open && 'rotate-180')} aria-hidden="true" />
          </button>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div id={panelId} initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="border-t border-border px-4 py-4">
                  <QuestionContent source={q.solution} className="text-body" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </article>
  );
}
