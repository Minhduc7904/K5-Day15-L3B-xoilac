'use client';

import { ArrowLeft, Bot, Download, Library, Play, Trophy } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import { useState } from 'react';
import { Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { studyApi } from '../api';
import { DIFFS } from '../create/plan';
import { diffColor, typeColor } from '../create/structure-preview';
import { ErrorState, PageContainer } from '../components/page-states';
import { QuestionContent } from '../components/question-content';
import { ScoreBadge } from '../components/score-badge';
import { chapterOf, difficultyLabels, typeLabels } from '../fixtures/chapters';
import { examDuration, formatDuration, longDate, relativeDay } from '../format';
import { formatScore } from '../grading';
import type { PublicQuestion } from '../types';
import { useResource } from '../use-resource';
import { ExamPaperDialog } from './exam-paper';

const ease = [0.16, 1, 0.3, 1] as const;
const ROMAN = ['I', 'II', 'III', 'IV'];
const diffText = { NB: 'text-success', TH: 'text-info', VD: 'text-warning', VDC: 'text-danger' } as const;

type Data = Awaited<ReturnType<typeof studyApi.getExam>>;

export function ExamDetailPage({ id }: { id: string }) {
  const res = useResource(() => studyApi.getExam(id), `exam-${id}`);

  return (
    <div className="min-h-[calc(100dvh-var(--student-header-height))] bg-surface">
      <PageContainer className="grid grid-cols-[minmax(0,1fr)] gap-5 sm:gap-6">
        <Link
          href="/exams"
          className="inline-flex w-fit items-center gap-1.5 rounded-lg text-label font-semibold text-muted-foreground hover:text-primary focus-visible:outline-2 focus-visible:outline-ring"
        >
          <ArrowLeft className="size-4" aria-hidden="true" /> Đề của tôi
        </Link>
        {res.status === 'loading' && (
          <div className="grid gap-5">
            <Skeleton className="h-72 rounded-3xl" />
            <Skeleton className="h-96 rounded-3xl" />
          </div>
        )}
        {res.status === 'error' && (
          <ErrorState
            title={res.error.name === 'NotFoundError' ? 'Không tìm thấy đề này' : undefined}
            message={res.error.name === 'NotFoundError' ? 'Có thể đề đã bị xoá hoặc đường dẫn sai.' : undefined}
            onRetry={res.error.name === 'NotFoundError' ? undefined : res.reload}
          />
        )}
        {res.status === 'ready' && <Detail {...res.data} />}
      </PageContainer>
    </div>
  );
}

function Detail({ exam, questions, attempts }: Data) {
  const [paper, setPaper] = useState(false);
  const byId = new Map(questions.map((q) => [q.id, q]));
  const sections = exam.sections
    .map((s) => ({ ...s, qs: s.questionIds.map((qid) => byId.get(qid)).filter((q): q is PublicQuestion => Boolean(q)) }))
    .filter((s) => s.qs.length);

  return (
    <>
      <Hero exam={exam} total={questions.length} attempts={attempts} onPaper={() => setPaper(true)} />

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Questions sections={sections} />
        <aside className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:sticky lg:top-[calc(var(--student-header-height)+1.25rem)]">
          <Structure sections={sections} total={questions.length} questions={questions} />
          <Attempts attempts={attempts} createdAt={exam.createdAt} />
        </aside>
      </div>

      <AnimatePresence>{paper && <ExamPaperDialog examId={exam.id} onClose={() => setPaper(false)} />}</AnimatePresence>
    </>
  );
}

/* ---------------- Đầu trang ---------------- */

function Hero({ exam, total, attempts, onPaper }: { exam: Data['exam']; total: number; attempts: Data['attempts']; onPaper: () => void }) {
  const reduce = useReducedMotion();
  const say = exam.reason ?? `Đề ${total} câu, ${examDuration(exam.durationMinutes).toLowerCase()}. Đọc lướt câu hỏi bên dưới rồi bắt đầu khi bạn sẵn sàng nhé!`;

  return (
    <section aria-labelledby="exam-title" className="relative isolate overflow-hidden rounded-3xl bg-primary text-primary-foreground shadow-lift">
      <div aria-hidden="true" className="bg-grid-inverse absolute inset-0 -z-10 [mask-image:linear-gradient(to_bottom,black,transparent_95%)]" />
      <div className="grid gap-6 p-5 sm:p-8 md:grid-cols-[minmax(0,1fr)_minmax(0,19rem)] md:items-end">
        <div className="grid gap-4">
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-primary-foreground/12 px-3 py-1 text-caption font-semibold">
            {exam.source === 'ai' ? <Bot className="size-3.5" aria-hidden="true" /> : <Library className="size-3.5" aria-hidden="true" />}
            {exam.source === 'ai' ? 'Tạo với AI' : 'Từ ngân hàng đề'} · {relativeDay(exam.createdAt)}
          </span>
          <h1 id="exam-title" className="text-h1 text-balance">{exam.title}</h1>
          <dl className="flex flex-wrap gap-x-6 gap-y-2">
            {[
              { k: 'Số câu', v: `${total} câu` },
              { k: 'Thời gian', v: examDuration(exam.durationMinutes) },
              { k: 'Số phần', v: `${exam.sections.length} phần` },
            ].map(({ k, v }) => (
              <div key={k} className="grid">
                <dt className="text-caption text-primary-foreground/65">{k}</dt>
                <dd className="text-body-lg font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Link
              href={`/exams/${exam.id}/take`}
              className="inline-flex h-12 items-center gap-2 rounded-xl bg-flame-strong px-6 text-body font-semibold text-primary-foreground transition-[background-color,transform] hover:bg-danger-hover active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <Play className="size-5" aria-hidden="true" />
              {attempts.length ? 'Làm lại đề này' : 'Bắt đầu làm bài'}
            </Link>
            <button
              type="button"
              onClick={onPaper}
              className="inline-flex h-12 items-center gap-2 rounded-xl border border-primary-foreground/25 px-5 text-label font-semibold transition-colors hover:border-primary-foreground/60 hover:bg-primary-foreground/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <Download className="size-4" aria-hidden="true" /> Tải đề
            </button>
            {attempts[0] && (
              <Link
                href={`/results/${attempts[0].id}`}
                className="inline-flex h-12 items-center rounded-xl px-3 text-label font-semibold text-primary-foreground/85 underline-offset-4 hover:text-primary-foreground hover:underline focus-visible:outline-2 focus-visible:outline-accent"
              >
                Kết quả gần nhất
              </Link>
            )}
          </div>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2">
          <motion.div
            className="relative mb-6 rounded-2xl rounded-br-sm bg-background px-4 py-3 text-label text-foreground shadow-soft"
            initial={reduce ? false : { opacity: 0, scale: 0.94, x: 6 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
            style={{ originX: 1, originY: 1 }}
          >
            <svg aria-hidden="true" viewBox="0 0 14 14" className="absolute -right-[11px] bottom-0 size-3.5 -scale-x-100 fill-background">
              <path d="M14 0v14H0C7 12 12 7 14 0z" />
            </svg>
            {exam.reason && <span className="mb-0.5 block text-caption font-semibold text-muted-foreground">Vì sao có đề này?</span>}
            {say}
            {exam.prompt && <span className="mt-1.5 block text-caption text-muted-foreground">Bạn đã nhắn: “{exam.prompt}”</span>}
          </motion.div>
          <motion.div
            className="w-20 sm:w-24"
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
          >
            <Image src="/brand/mascot/static/studying.webp" alt="" width={192} height={192} unoptimized className="pixelated h-auto w-full drop-shadow-[0_10px_14px_rgb(3_23_47/0.45)]" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Câu hỏi ---------------- */

type Section = Data['exam']['sections'][number] & { qs: PublicQuestion[] };

function Questions({ sections }: { sections: Section[] }) {
  const [active, setActive] = useState(0);
  const section = sections[active];

  return (
    <section aria-labelledby="questions-title" className="grid grid-cols-[minmax(0,1fr)] gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="questions-title" className="text-h3 text-foreground">Câu hỏi trong đề</h2>
          <p className="text-caption text-muted-foreground">Đáp án và lời giải hiện sau khi bạn nộp bài. Bấm vào hình để xem to.</p>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Chọn phần"
        className="sticky top-[calc(var(--student-header-height)+0.5rem)] z-10 flex gap-1 overflow-x-auto rounded-2xl bg-background p-1 shadow-soft [scrollbar-width:none]"
      >
        {sections.map((s, i) => (
          <button
            key={s.id}
            id={`part-tab-${i}`}
            role="tab"
            type="button"
            aria-selected={active === i}
            aria-controls="part-panel"
            onClick={() => setActive(i)}
            className={cn(
              'relative flex min-h-11 flex-1 shrink-0 items-center justify-center gap-2 rounded-xl px-3 text-label font-semibold whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
              active === i ? 'text-primary-foreground' : 'text-muted-foreground hover:bg-surface hover:text-foreground',
            )}
          >
            {active === i && <motion.span layoutId="part-tab" className="absolute inset-0 rounded-xl bg-primary" transition={{ type: 'spring', stiffness: 420, damping: 36 }} />}
            <span className="relative flex items-center gap-2">
              <i className={cn('size-2.5 rounded-full', typeColor[s.type], active === i && 'ring-2 ring-primary-foreground/70')} aria-hidden="true" />
              Phần {ROMAN[i]}
              <span className="hidden font-medium opacity-80 sm:inline">· {typeLabels[s.type]}</span>
              <span className={cn('rounded-full px-1.5 text-caption tabular-nums', active === i ? 'bg-primary-foreground/20' : 'bg-surface-muted')}>{s.qs.length}</span>
            </span>
          </button>
        ))}
      </div>

      {section && (
        <ol id="part-panel" role="tabpanel" aria-labelledby={`part-tab-${active}`} className="grid gap-4">
          {section.qs.map((q, i) => (
            <QuestionCard key={q.id} n={i + 1} q={q} />
          ))}
        </ol>
      )}
    </section>
  );
}

function QuestionCard({ n, q }: { n: number; q: PublicQuestion }) {
  const longest = Math.max(0, ...q.statements.map((s) => s.content.length));
  const twoCols = q.type === 'SINGLE_CHOICE' && longest <= 48;

  return (
    <li className="rounded-2xl bg-background p-4 shadow-soft sm:p-6">
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="flex h-8 min-w-8 items-center justify-center rounded-lg bg-primary px-2 text-label font-bold text-primary-foreground tabular-nums">
          <span className="sr-only">Câu </span>
          {n}
        </span>
        <span className={cn('inline-flex items-center gap-1.5 text-caption font-semibold', diffText[q.difficulty])}>
          <i className={cn('size-2 rounded-full', diffColor[q.difficulty])} aria-hidden="true" />
          {difficultyLabels[q.difficulty]}
        </span>
        <span className="min-w-0 truncate text-caption text-muted-foreground">{chapterOf(q.chapter).name}</span>
      </div>

      <QuestionContent source={q.content} className="text-body-lg" />

      {q.type === 'SINGLE_CHOICE' && q.statements.length > 0 && (
        <ul className={cn('mt-4 grid gap-2', twoCols && 'sm:grid-cols-2')}>
          {q.statements.map((s) => (
            <li key={s.label} className="flex items-start gap-3 rounded-xl border border-border px-3 py-2.5 text-body">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full border-2 border-primary/25 text-caption font-bold text-primary">{s.label}</span>
              <QuestionContent source={s.content} inline className="min-w-0 self-center" />
            </li>
          ))}
        </ul>
      )}

      {q.type === 'TRUE_FALSE' && q.statements.length > 0 && (
        <ul className="mt-4 divide-y divide-border overflow-hidden rounded-xl border border-border">
          {q.statements.map((s) => (
            <li key={s.label} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-3 py-2.5 text-body">
              <b className="w-5 text-primary">{s.label})</b>
              <QuestionContent source={s.content} inline className="min-w-0" />
              <span className="flex gap-1 text-caption font-semibold text-muted-foreground" aria-hidden="true">
                <span className="rounded-md border border-border px-1.5 py-0.5">Đ</span>
                <span className="rounded-md border border-border px-1.5 py-0.5">S</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {q.type === 'SHORT_ANSWER' && (
        <p className="mt-4 flex items-center gap-3 rounded-xl border-2 border-dashed border-border px-3 py-2.5 text-caption text-muted-foreground">
          <span className="flex gap-1" aria-hidden="true">
            {Array.from({ length: 4 }, (_, i) => (
              <span key={i} className="size-6 rounded-md border border-border bg-surface" />
            ))}
          </span>
          Điền đáp án số khi làm bài
        </p>
      )}
    </li>
  );
}

/* ---------------- Cột phụ ---------------- */

function Structure({ sections, total, questions }: { sections: Section[]; total: number; questions: PublicQuestion[] }) {
  const diffs = DIFFS.map((d) => ({ d, n: questions.filter((q) => q.difficulty === d).length })).filter((x) => x.n);
  const chapters = [...new Set(questions.map((q) => q.chapter))]
    .map((c) => ({ c, n: questions.filter((q) => q.chapter === c).length }))
    .sort((a, b) => b.n - a.n);

  return (
    <section aria-labelledby="structure-title" className="grid gap-4 rounded-2xl bg-background p-5 shadow-soft">
      <h2 id="structure-title" className="text-h3 text-foreground">Cấu trúc đề</h2>

      <div className="grid gap-2">
        <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
          {sections.map((s) => (
            <span key={s.id} className={cn('first:rounded-l-full last:rounded-r-full', typeColor[s.type])} style={{ width: `${(s.qs.length / total) * 100}%` }} />
          ))}
        </div>
        <ul className="grid gap-1">
          {sections.map((s, i) => (
            <li key={s.id} className="flex items-center justify-between gap-3 text-label">
              <span className="flex items-center gap-2 text-muted-foreground">
                <i className={cn('size-2.5 rounded-full', typeColor[s.type])} aria-hidden="true" />
                Phần {ROMAN[i]} · {typeLabels[s.type]}
              </span>
              <b className="font-semibold text-foreground tabular-nums">{s.qs.length}</b>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-2 border-t border-border pt-4">
        <p className="text-caption font-semibold text-muted-foreground">Mức độ</p>
        <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" aria-hidden="true">
          {diffs.map(({ d, n }, i) => (
            <motion.span
              key={d}
              className={cn('first:rounded-l-full last:rounded-r-full', diffColor[d])}
              initial={{ width: 0 }}
              animate={{ width: `${(n / total) * 100}%` }}
              transition={{ delay: 0.15 + i * 0.08, duration: 0.6, ease }}
            />
          ))}
        </div>
        <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
          {diffs.map(({ d, n }) => (
            <li key={d} className="flex items-center justify-between gap-2 text-caption text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <i className={cn('size-2 rounded-full', diffColor[d])} aria-hidden="true" />
                {difficultyLabels[d]}
              </span>
              <b className="text-foreground tabular-nums">{n}</b>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-2 border-t border-border pt-4">
        <p className="text-caption font-semibold text-muted-foreground">Theo chương</p>
        <ul className="grid gap-1.5">
          {chapters.map(({ c, n }) => (
            <li key={c} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 text-label">
              <span className="truncate text-foreground" title={chapterOf(c).name}>{chapterOf(c).name}</span>
              <span className="text-caption text-muted-foreground tabular-nums">{n} câu</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Attempts({ attempts, createdAt }: { attempts: Data['attempts']; createdAt: string }) {
  const best = attempts.length ? Math.max(...attempts.map((a) => a.score)) : null;
  return (
    <section aria-labelledby="attempts-title" className="rounded-2xl bg-background p-5 shadow-soft">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 id="attempts-title" className="text-h3 text-foreground">Lượt làm bài</h2>
        {best !== null && (
          <span className="inline-flex items-center gap-1 text-caption font-semibold text-success">
            <Trophy className="size-4" aria-hidden="true" /> Cao nhất {formatScore(best)}
          </span>
        )}
      </div>
      {attempts.length === 0 ? (
        <p className="text-label text-muted-foreground">Chưa làm lần nào. Bài tự lưu khi bạn chọn đáp án, lỡ tải lại trang cũng không mất.</p>
      ) : (
        <ul className="-mx-2 grid gap-0.5">
          {attempts.map((a, i) => (
            <li key={a.id}>
              <Link href={`/results/${a.id}`} className="flex items-center gap-3 rounded-xl p-2 transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring">
                <ScoreBadge score={a.score} />
                <span className="grid">
                  <span className="text-label font-semibold text-foreground">Lần {attempts.length - i}</span>
                  <span className="text-caption text-muted-foreground">
                    {relativeDay(a.submittedAt)} · {formatDuration(a.durationSeconds)}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 border-t border-border pt-3 text-caption text-muted-foreground">Tạo lúc {longDate(createdAt)}. Điểm là điểm luyện tập, không phải điểm chính thức.</p>
    </section>
  );
}
