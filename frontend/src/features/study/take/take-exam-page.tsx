'use client';

import { ArrowLeft, ArrowRight, Bookmark, CheckCheck, Clock3, Grid3x3, LogOut, Play, RotateCcw, Send, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Logo } from '@/components/layout/logo';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { cn } from '@/lib/cn';
import { studyApi } from '../api';
import { answerValues, attemptApi, attemptError, attemptResultId, type AttemptState, type AttemptSummary } from '../attempt-api';
import { ErrorState } from '../components/page-states';
import { QuestionContent } from '../components/question-content';
import { chapterOf, difficultyLabels, typeLabels } from '../fixtures/chapters';
import { clock, examDuration } from '../format';
import { adaptDraft } from '../exam-chat-api';
import type { Answer, Exam, PublicQuestion } from '../types';
import { useResource } from '../use-resource';
import { useOnlineAttempt } from './use-online-attempt';

interface Draft {
  startedAt: string;
  answers: Record<string, Answer>;
  flags: string[];
  current: number;
  /** Giây đã mở từng câu. */
  times?: Record<string, number>;
}

const draftKey = (examId: string) => `examind:attempt-draft:${examId}`;

function readDraft(examId: string): Draft | null {
  try {
    const raw = window.localStorage.getItem(draftKey(examId));
    return raw ? (JSON.parse(raw) as Draft) : null;
  } catch {
    return null;
  }
}

const writeDraft = (examId: string, draft: Draft) => {
  try {
    window.localStorage.setItem(draftKey(examId), JSON.stringify(draft));
  } catch {
    // Không lưu được thì vẫn làm bài bình thường trong phiên này.
  }
};

const clearDraft = (examId: string) => {
  try {
    window.localStorage.removeItem(draftKey(examId));
  } catch {
    // bỏ qua
  }
};

export const isAnswered = (a: Answer | undefined) =>
  a !== undefined && a !== null && (typeof a === 'string' ? a.trim() !== '' : a.some((v) => v !== null));

export function TakeExamPage({ id }: { id: string }) {
  const res = useResource(() => studyApi.getExam(id), `take-${id}`);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [existing, setExisting] = useState<Draft | null | undefined>(undefined);

  useEffect(() => setExisting(readDraft(id)), [id]);

  if (res.status === 'error') {
    return (
      <div className="mx-auto max-w-xl p-6">
        <ErrorState title="Không mở được đề" onRetry={res.reload} />
      </div>
    );
  }
  if (res.status === 'loading' || existing === undefined) {
    return (
      <div className="mx-auto grid max-w-3xl gap-4 p-6" aria-busy="true">
        <Skeleton className="h-14 rounded-2xl" />
        <Skeleton className="h-96 rounded-3xl" />
      </div>
    );
  }

  const { exam, questions, activeAttempt } = res.data;
  if (exam.remote) return <OnlineTake exam={exam} count={questions.length} latest={activeAttempt} />;
  if (!draft) {
    return (
      <StartScreen
        exam={exam}
        count={questions.length}
        existing={existing}
        onStart={(resume) => {
          const next = resume && existing ? existing : { startedAt: new Date().toISOString(), answers: {}, flags: [], current: 0 };
          writeDraft(exam.id, next);
          setDraft(next);
        }}
      />
    );
  }
  return <ExamRunner exam={exam} questions={questions} initial={draft} />;
}

function OnlineTake({ exam, count, latest }: { exam: Exam; count: number; latest: AttemptSummary | null }) {
  const [active, setActive] = useState<AttemptState | null>(null);
  const [last, setLast] = useState(latest);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function start() {
    setBusy(true);
    setError(undefined);
    try {
      const next = await attemptApi.start(exam.id, last?.status === 'graded');
      if (next.status === 'graded') setLast(next);
      else setActive(next);
    } catch (failure) {
      setError(attemptError(failure).message);
    } finally {
      setBusy(false);
    }
  }

  const existing = last?.status === 'in_progress'
    ? { startedAt: last.started_at, answers: answerValues(last), current: 0, flags: [] } : null;
  if (!active) return <StartScreen exam={exam} count={count} existing={existing} onStart={start}
    latest={last} error={error} busy={busy} />;
  const fixed = adaptDraft(active.draft);
  const initial = { startedAt: active.started_at, answers: answerValues(active), flags: [],
    current: Math.max(0, fixed.questions.findIndex((question) => question.id === active.current)) };
  return <ExamRunner key={active.attempt_id} exam={fixed.exam} questions={fixed.questions} initial={initial} remote={active} />;
}

function StartScreen({ exam, count, existing, onStart, latest, busy, error }: {
  exam: Exam; count: number; existing: Draft | null; onStart: (resume: boolean) => void;
  latest?: AttemptSummary | null; busy?: boolean; error?: string;
}) {
  const answered = existing ? Object.values(existing.answers).filter(isAnswered).length : 0;
  return (
    <div className="grid min-h-dvh place-items-center bg-gradient-to-b from-primary-subtle to-surface px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} className="grid w-full max-w-lg justify-items-center gap-5 rounded-[2rem] bg-background p-6 text-center shadow-lift sm:p-8">
        <motion.div animate={{ y: [0, -6, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}>
          <Image src="/brand/mascot/static/studying.webp" alt="" width={384} height={384} className="h-auto w-32" priority />
        </motion.div>
        <div className="grid gap-1.5">
          <p className="text-label font-semibold text-accent-strong">Sẵn sàng chưa?</p>
          <h1 className="text-h2 text-balance text-foreground">{exam.title}</h1>
          <p className="text-body text-muted-foreground">
            {count} câu · {examDuration(exam.durationMinutes)} · {exam.sections.length} phần
          </p>
        </div>
        <ul className="grid w-full gap-2 rounded-2xl bg-surface p-4 text-left text-caption text-muted-foreground">
          <li>• Chọn đáp án là bài tự lưu. Tải lại trang vẫn làm tiếp được.</li>
          <li>• Phím tắt: A–D chọn đáp án, ← → chuyển câu, F đánh dấu xem lại.</li>
          <li>• {exam.durationMinutes > 0 ? 'Hết giờ bài tự nộp.' : 'Đề không giới hạn thời gian, nộp khi bạn xong.'} Điểm là điểm luyện tập, không chính thức.</li>
        </ul>
        {error && <p role="alert" className="text-label text-danger">{error}</p>}
        {latest?.status === 'graded' && (
          <p className="text-label text-muted-foreground">
            {latest.reason === 'timeout' && 'Hết giờ làm bài. Bài đã được tự động nộp và chấm. '}
            <Link className="font-semibold text-primary underline" href={`/results/${attemptResultId(latest.attempt_id)}`}>
              Xem kết quả
            </Link>
          </p>
        )}
        {existing ? (
          <div className="grid w-full gap-2">
            <Button size="lg" fullWidth loading={busy} leftIcon={<Play aria-hidden="true" />} onClick={() => onStart(true)} data-autofocus autoFocus>
              Làm tiếp ({answered}/{count} câu đã trả lời)
            </Button>
            {!exam.remote && <Button size="lg" variant="outline" fullWidth leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => onStart(false)}>
              Làm lại từ đầu
            </Button>}
          </div>
        ) : (
          <Button size="lg" fullWidth loading={busy} leftIcon={<Play aria-hidden="true" />} onClick={() => onStart(false)} data-autofocus autoFocus>
            {latest?.status === 'graded' ? 'Làm lại đề này' : 'Bắt đầu làm bài'}
          </Button>
        )}
        <Link href={`/exams/${exam.id}`} className="rounded-lg text-label font-semibold text-muted-foreground hover:text-primary focus-visible:outline-2 focus-visible:outline-ring">
          Quay lại chi tiết đề
        </Link>
      </motion.div>
    </div>
  );
}

function ExamRunner({ exam, questions, initial, remote }: {
  exam: Exam; questions: PublicQuestion[]; initial: Draft; remote?: AttemptState;
}) {
  const router = useRouter();
  const toast = useToast();
  const [localAnswers, setAnswers] = useState(initial.answers);
  const [flags, setFlags] = useState<string[]>(initial.flags);
  const [times, setTimes] = useState<Record<string, number>>(initial.times ?? {});
  const [current, setCurrent] = useState(Math.min(initial.current, questions.length - 1));
  const [direction, setDirection] = useState(1);
  const [now, setNow] = useState(() => performance.now());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const submittedRef = useRef(false);

  const q = questions[current];
  const online = useOnlineAttempt(remote, q.id);
  const answers = remote ? online.answers : localAnswers;
  const untimed = remote ? remote.deadline_at === null : exam.durationMinutes <= 0;
  const deadline = remote?.deadline_at ? Date.parse(remote.deadline_at) : Date.parse(initial.startedAt) + exam.durationMinutes * 60_000;
  const serverNow = remote ? online.clock.now + Math.max(0, now - online.clock.local) : Date.now();
  const remaining = Math.max(0, Math.ceil((deadline - serverNow) / 1000));
  const ended = Boolean(remote && (online.state?.status === 'graded' || (!untimed && remaining <= 0)));
  const locked = ended || submitting;
  const answeredCount = questions.filter((q) => isAnswered(answers[q.id])).length;

  // Vị trí câu trong phần, để hiện "Phần 2 · câu 1".
  const sectionOf = useMemo(() => {
    const map = new Map<string, { index: number; title: string }>();
    exam.sections.forEach((s, i) => s.questionIds.forEach((qid) => map.set(qid, { index: i, title: s.title })));
    return map;
  }, [exam]);

  useEffect(() => {
    if (untimed) return;
    const t = window.setInterval(() => setNow(performance.now()), 250);
    return () => window.clearInterval(t);
  }, [untimed]);

  useEffect(() => {
    if (!remote) writeDraft(exam.id, { startedAt: initial.startedAt, answers: localAnswers, flags, current, times });
  }, [remote, exam.id, initial.startedAt, localAnswers, flags, current, times]);

  // Cộng thời gian cho câu đang mở, mỗi giây một lần; bỏ qua lúc tab bị ẩn.
  const currentId = questions[current]?.id;
  useEffect(() => {
    if (remote || !currentId) return;
    const t = window.setInterval(() => {
      if (document.visibilityState === 'visible' && !submittedRef.current) setTimes((m) => ({ ...m, [currentId]: (m[currentId] ?? 0) + 1 }));
    }, 1000);
    return () => window.clearInterval(t);
  }, [currentId, remote]);

  const { flush, sync, checkpoint, apply } = online;

  const submit = useCallback(
    async (auto = false) => {
      if (submittedRef.current) return;
      submittedRef.current = true;
      setSubmitting(true);
      try {
        if (remote) {
          checkpoint(q.id, true);
          if (!await flush()) throw new Error('Đáp án chưa được đồng bộ. Hãy lưu xong rồi nộp lại.');
          apply(await attemptApi.submit(remote.attempt_id));
          return;
        }
        const attempt = await studyApi.submitAttempt(exam.id, localAnswers, initial.startedAt, times);
        clearDraft(exam.id);
        if (auto) toast({ tone: 'info', title: 'Hết giờ, bài đã được nộp' });
        router.push(`/results/${attempt.id}`);
      } catch (error) {
        submittedRef.current = false;
        setSubmitting(false);
        toast({ tone: 'danger', title: 'Chưa nộp được bài', description:
          remote && error instanceof Error ? error.message : 'Bài vẫn được lưu trên máy. Kiểm tra mạng rồi nộp lại nhé.' });
      }
    },
    [remote, checkpoint, flush, apply, q.id, localAnswers, exam.id, initial.startedAt, router, toast, times],
  );

  useEffect(() => {
    if (!remote && !untimed && remaining <= 0) void submit(true);
  }, [remote, untimed, remaining, submit]);

  useEffect(() => {
    if (!ended || online.state?.status === 'graded') return;
    const check = () => { void sync().catch(() => undefined); };
    check();
    const interval = window.setInterval(check, 2000);
    return () => window.clearInterval(interval);
  }, [ended, online.state?.status, sync]);

  const redirected = useRef(false);
  useEffect(() => {
    if (online.state?.status !== 'graded' || redirected.current) return;
    redirected.current = true;
    if (online.state.reason === 'timeout') {
      toast({ tone: 'info', title: 'Hết giờ làm bài. Bài đã được tự động nộp và chấm.',
        description: online.pendingAnswers > 0 ? 'Các thay đổi chưa được máy chủ xác nhận lưu không được chấm.' : undefined });
    }
    online.clearPending();
    router.replace(`/results/${attemptResultId(online.state.attempt_id)}`);
  }, [online, router, toast]);

  const go = useCallback(
    (index: number) => {
      if (index < 0 || index >= questions.length) return;
      setDirection(index > current ? 1 : -1);
      setCurrent(index);
      setNavOpen(false);
      if (remote) void flush();
    },
    [current, questions.length, remote, flush],
  );

  const changeRemote = online.change;
  const setAnswer = useCallback((value: Answer | ((prev: Answer) => Answer)) => {
    if (locked) return;
    if (remote) changeRemote(q.id, value, q.type === 'SHORT_ANSWER');
    else setAnswers((a) => ({ ...a, [q.id]: typeof value === 'function' ? value(a[q.id] ?? null) : value }));
  }, [locked, remote, changeRemote, q.id, q.type]);
  const toggleFlag = useCallback(() => setFlags((f) => (f.includes(q.id) ? f.filter((x) => x !== q.id) : [...f, q.id])), [q.id]);

  // Phím tắt (không bắt khi đang gõ trong ô nhập).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (locked || target.closest('input, textarea, [contenteditable="true"]') || confirmOpen || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'ArrowRight') go(current + 1);
      else if (e.key === 'ArrowLeft') go(current - 1);
      else if (e.key.toLowerCase() === 'f') toggleFlag();
      else if (q.type === 'SINGLE_CHOICE') {
        const idx = 'abcd'.indexOf(e.key.toLowerCase());
        if (idx >= 0 && q.statements[idx]) setAnswer(q.statements[idx].label);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [current, go, q, toggleFlag, confirmOpen, locked, setAnswer]);

  const lowTime = !untimed && remaining <= 300;
  const criticalTime = !untimed && remaining <= 60;
  const section = sectionOf.get(q.id);

  return (
    <div className="min-h-dvh bg-surface">
      {/* Thanh trên */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
          <div className="hidden sm:block">
            <Logo variant="mark" href={`/exams/${exam.id}`} />
          </div>
          <div className="grid min-w-0 flex-1">
            <p className="truncate text-label font-semibold text-foreground">{exam.title}</p>
            <p className="text-caption text-muted-foreground tabular-nums">
              Đã trả lời {answeredCount}/{questions.length}
              {remote && <span aria-live="polite"> · {online.error ? 'Chưa đồng bộ' : online.pendingAnswers ? 'Đang lưu' : 'Đã lưu'}</span>}
            </p>
          </div>
          <motion.div
            role={untimed ? undefined : 'timer'}
            aria-live={criticalTime ? 'assertive' : 'off'}
            aria-label={untimed ? undefined : `Còn lại ${clock(remaining)}`}
            animate={criticalTime ? { scale: [1, 1.06, 1] } : { scale: 1 }}
            transition={criticalTime ? { duration: 1, repeat: Infinity } : undefined}
            className={cn(
              'flex items-center gap-1.5 rounded-2xl px-3 py-2 text-body font-bold tabular-nums',
              criticalTime ? 'bg-danger text-primary-foreground' : lowTime ? 'bg-warning-subtle text-warning' : 'bg-surface text-foreground',
            )}
          >
            <Clock3 className="size-4" aria-hidden="true" />
            {untimed ? 'Không giới hạn' : clock(remaining)}
          </motion.div>
          <Button disabled={locked} onClick={() => setConfirmOpen(true)} leftIcon={<Send aria-hidden="true" />} className="hidden sm:inline-flex">
            Nộp bài
          </Button>
        </div>
        <div className="h-1 bg-surface-muted" aria-hidden="true">
          <motion.div className="h-full bg-gradient-to-r from-primary to-accent" animate={{ width: `${(answeredCount / questions.length) * 100}%` }} transition={{ type: 'spring', stiffness: 120, damping: 20 }} />
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-[minmax(0,1fr)] gap-6 px-4 py-6 pb-32 sm:px-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:pb-10">
        {/* Câu hỏi */}
        <main id="noi-dung" className="min-w-0">
          {ended && <p role="status" className="mb-4 rounded-xl bg-warning-subtle p-4 text-label text-warning">
            {online.state?.reason === 'manual' ? 'Bài đã được nộp. Đang tải kết quả…' : 'Hết giờ làm bài. Đang tải kết quả…'}
          </p>}
          {!ended && online.error && (
            <div className="mb-4 grid gap-2 rounded-xl bg-warning-subtle p-4 text-label text-warning">
              <p role="status">{online.error.message}</p>
              <div className="flex flex-wrap gap-2">
                {online.conflict ? (
                  <>
                    <Button size="sm" onClick={() => void online.resolveConflict(true)}>Lưu đáp án của tab này</Button>
                    <Button size="sm" variant="outline" onClick={() => void online.resolveConflict(false)}>Giữ đáp án đã lưu</Button>
                  </>
                ) : <Button size="sm" variant="outline" onClick={() => void flush()}>Thử lưu lại</Button>}
              </div>
            </div>
          )}
          <AnimatePresence mode="wait" custom={direction} initial={false}>
            <motion.article
              key={q.id}
              custom={direction}
              initial={{ opacity: 0, x: direction * 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: direction * -40 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              aria-labelledby="question-title"
              className="grid gap-5 rounded-3xl border border-border bg-background p-5 shadow-soft sm:p-8"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 id="question-title" className="rounded-xl bg-primary px-3 py-1 text-label font-bold text-primary-foreground">
                    Câu {current + 1}
                    <span className="font-normal opacity-80">/{questions.length}</span>
                  </h1>
                  {section && <span className="text-caption font-semibold text-muted-foreground">{section.title}</span>}
                  <span className="rounded-lg bg-surface px-2 py-0.5 text-caption text-muted-foreground">{difficultyLabels[q.difficulty]}</span>
                  {q.maxPoints !== undefined && <span className="text-caption text-muted-foreground">
                    {q.maxPoints.toLocaleString('vi-VN', { maximumFractionDigits: 3 })} điểm
                  </span>}
                </div>
                <button
                  type="button"
                  onClick={toggleFlag}
                  aria-pressed={flags.includes(q.id)}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-caption font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                    flags.includes(q.id) ? 'bg-warning-subtle text-warning' : 'text-muted-foreground hover:bg-surface hover:text-foreground',
                  )}
                >
                  <Bookmark className={cn('size-4', flags.includes(q.id) && 'fill-current')} aria-hidden="true" />
                  {flags.includes(q.id) ? 'Đã đánh dấu' : 'Xem lại sau'}
                </button>
              </div>

              <p className="text-caption text-muted-foreground">{chapterOf(q.chapter).name}</p>
              <QuestionContent source={q.content} draftId={q.remoteDraftId} attemptId={remote?.attempt_id} />

              <fieldset disabled={locked} className="min-w-0" onBlur={remote ? () => void flush() : undefined}>
                <AnswerInput question={q} value={answers[q.id] ?? null} onChange={setAnswer} attemptId={remote?.attempt_id} />
              </fieldset>
            </motion.article>
          </AnimatePresence>

          <div className="mt-4 flex items-center justify-between gap-3">
            <Button variant="outline" leftIcon={<ArrowLeft aria-hidden="true" />} onClick={() => go(current - 1)} disabled={current === 0}>
              Câu trước
            </Button>
            {current < questions.length - 1 ? (
              <Button rightIcon={<ArrowRight aria-hidden="true" />} onClick={() => go(current + 1)}>
                Câu tiếp
              </Button>
            ) : (
              <Button disabled={locked} variant="accent" leftIcon={<CheckCheck aria-hidden="true" />} onClick={() => setConfirmOpen(true)}>
                Xong, nộp bài
              </Button>
            )}
          </div>
        </main>

        {/* Bảng câu hỏi (máy tính) */}
        <aside className="hidden lg:block">
          <div className="sticky top-24 grid gap-4 rounded-3xl border border-border bg-background p-5 shadow-soft">
            <Navigator exam={exam} questions={questions} answers={answers} flags={flags} current={current} onGo={go} />
            <Button disabled={locked} fullWidth leftIcon={<Send aria-hidden="true" />} onClick={() => setConfirmOpen(true)}>
              Nộp bài
            </Button>
            <Link href={`/exams/${exam.id}`} onClick={remote ? () => checkpoint(q.id, true) : undefined} className="inline-flex items-center justify-center gap-1.5 rounded-lg text-caption font-semibold text-muted-foreground hover:text-primary focus-visible:outline-2 focus-visible:outline-ring">
              <LogOut className="size-3.5" aria-hidden="true" /> Thoát (bài vẫn được lưu)
            </Link>
          </div>
        </aside>
      </div>

      {/* Thanh dưới (điện thoại) */}
      <div className="fixed inset-x-0 bottom-0 z-30 flex gap-2 border-t border-border bg-background/95 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur lg:hidden">
        <Button variant="outline" leftIcon={<Grid3x3 aria-hidden="true" />} onClick={() => setNavOpen(true)} className="flex-1">
          Câu {current + 1}/{questions.length}
        </Button>
        <Button disabled={locked} leftIcon={<Send aria-hidden="true" />} onClick={() => setConfirmOpen(true)} className="flex-1">
          Nộp bài
        </Button>
      </div>

      <AnimatePresence>
        {navOpen && (
          <Sheet title="Danh sách câu hỏi" onClose={() => setNavOpen(false)}>
            <Navigator exam={exam} questions={questions} answers={answers} flags={flags} current={current} onGo={go} />
          </Sheet>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {confirmOpen && !ended && (
          <ConfirmSubmit
            total={questions.length}
            answered={answeredCount}
            flagged={flags.length}
            submitting={submitting}
            onCancel={() => setConfirmOpen(false)}
            onConfirm={() => void submit()}
            onReview={() => {
              const firstOpen = questions.findIndex((x) => !isAnswered(answers[x.id]) || flags.includes(x.id));
              setConfirmOpen(false);
              if (firstOpen >= 0) go(firstOpen);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ---------------- Ô trả lời theo loại câu ---------------- */

function AnswerInput({ question, value, onChange, attemptId }: {
  question: PublicQuestion; value: Answer; onChange: (v: Answer | ((prev: Answer) => Answer)) => void; attemptId?: number;
}) {
  if (question.type === 'SINGLE_CHOICE') {
    return (
      <div role="radiogroup" aria-label="Chọn một đáp án" className="grid gap-2.5 sm:grid-cols-2">
        {question.statements.map((s) => {
          const selected = value === s.label;
          return (
            <motion.button
              key={s.label}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(selected ? null : s.label)}
              whileTap={{ scale: 0.98 }}
              className={cn(
                'flex items-center gap-3 rounded-2xl border-2 p-3.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                selected ? 'border-primary bg-primary-subtle' : 'border-border bg-background hover:border-primary/40 hover:bg-surface',
              )}
            >
              <span
                className={cn(
                  'flex size-9 shrink-0 items-center justify-center rounded-xl text-label font-bold transition-colors',
                  selected ? 'bg-primary text-primary-foreground' : 'bg-surface-muted text-muted-foreground',
                )}
              >
                {s.label}
              </span>
              <span className="min-w-0 text-body text-foreground">
                <QuestionContent source={s.content} draftId={question.remoteDraftId} attemptId={attemptId} inline />
              </span>
            </motion.button>
          );
        })}
      </div>
    );
  }

  if (question.type === 'TRUE_FALSE') {
    const picks = Array.isArray(value) ? value : question.statements.map(() => null);
    const empty = question.statements.map(() => null);
    // Cập nhật theo giá trị mới nhất, để bấm nhanh nhiều ý liên tiếp không bị ghi đè.
    const set = (i: number, v: boolean) =>
      onChange((prev) => (Array.isArray(prev) ? prev : empty).map((p, j) => (j === i ? (p === v ? null : v) : p)));
    return (
      <ol className="grid gap-2.5">
        {question.statements.map((s, i) => (
          <li key={s.label} className="flex flex-col gap-3 rounded-2xl border border-border bg-surface/60 p-3.5 sm:flex-row sm:items-center">
            <div className="flex min-w-0 flex-1 gap-2 text-body text-foreground">
              <b className="text-primary">{s.label})</b>
              <QuestionContent source={s.content} draftId={question.remoteDraftId} attemptId={attemptId} inline />
            </div>
            <div role="radiogroup" aria-label={`Ý ${s.label}`} className="flex shrink-0 gap-1.5 self-end sm:self-auto">
              {[
                { v: true, label: 'Đúng' },
                { v: false, label: 'Sai' },
              ].map((opt) => {
                const on = picks[i] === opt.v;
                return (
                  <button
                    key={opt.label}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => set(i, opt.v)}
                    className={cn(
                      'min-w-16 rounded-xl border-2 px-3 py-1.5 text-label font-bold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                      on
                        ? opt.v
                          ? 'border-success bg-success text-primary-foreground'
                          : 'border-danger bg-danger text-primary-foreground'
                        : 'border-border bg-background text-muted-foreground hover:border-foreground/30',
                    )}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <div className="grid gap-2">
      <label htmlFor={`short-${question.id}`} className="text-label font-semibold text-foreground">
        Đáp án của bạn
      </label>
      <input
        id={`short-${question.id}`}
        inputMode="decimal"
        autoComplete="off"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value.replace(/[^0-9,.\-]/g, '').slice(0, 8))}
        placeholder="Vd: 1,39"
        aria-describedby={`short-hint-${question.id}`}
        className="h-14 w-full max-w-xs rounded-2xl border-2 border-input bg-background px-4 text-h3 font-bold text-foreground tabular-nums outline-none placeholder:font-normal placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20"
      />
      <p id={`short-hint-${question.id}`} className="text-caption text-muted-foreground">
        Chỉ nhập số (tối đa 4 ký tự số như đề thật), dùng dấu phẩy cho phần thập phân.
      </p>
    </div>
  );
}

/* ---------------- Bảng câu hỏi ---------------- */

function Navigator({
  exam,
  questions,
  answers,
  flags,
  current,
  onGo,
}: {
  exam: Exam;
  questions: PublicQuestion[];
  answers: Record<string, Answer>;
  flags: string[];
  current: number;
  onGo: (i: number) => void;
}) {
  const indexOf = new Map(questions.map((q, i) => [q.id, i]));
  return (
    <nav aria-label="Danh sách câu hỏi" className="grid gap-4">
      {exam.sections.map((s) => (
        <div key={s.id} className="grid gap-2">
          <p className="text-caption font-semibold text-muted-foreground">
            {s.title.replace(/^Phần \d+: /, '')} · {typeLabels[s.type]}
          </p>
          <ol className="grid grid-cols-6 gap-1.5">
            {s.questionIds.map((qid) => {
              const i = indexOf.get(qid)!;
              const answered = isAnswered(answers[qid]);
              const flagged = flags.includes(qid);
              const isCurrent = i === current;
              return (
                <li key={qid}>
                  <button
                    type="button"
                    onClick={() => onGo(i)}
                    aria-current={isCurrent ? 'step' : undefined}
                    aria-label={`Câu ${i + 1}${answered ? ', đã trả lời' : ', chưa trả lời'}${flagged ? ', đã đánh dấu' : ''}`}
                    className={cn(
                      'relative flex aspect-square w-full items-center justify-center rounded-xl text-caption font-bold tabular-nums transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                      answered ? 'bg-primary text-primary-foreground' : 'bg-surface-muted text-muted-foreground hover:bg-border',
                      isCurrent && 'ring-2 ring-accent ring-offset-2 ring-offset-background',
                    )}
                  >
                    {i + 1}
                    {flagged && <span className="absolute -top-1 -right-1 size-3 rounded-full border-2 border-background bg-warning" aria-hidden="true" />}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      ))}
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[0.6875rem] text-muted-foreground" aria-hidden="true">
        <li className="inline-flex items-center gap-1"><i className="size-2.5 rounded bg-primary" /> Đã trả lời</li>
        <li className="inline-flex items-center gap-1"><i className="size-2.5 rounded bg-surface-muted ring-1 ring-border" /> Chưa trả lời</li>
        <li className="inline-flex items-center gap-1"><i className="size-2.5 rounded-full bg-warning" /> Xem lại</li>
      </ul>
    </nav>
  );
}

function Sheet({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <motion.div className="absolute inset-0 bg-foreground/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
      <motion.div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        className="absolute inset-x-0 bottom-0 max-h-[80dvh] overflow-y-auto rounded-t-3xl bg-background p-5 pb-8 shadow-lift outline-none"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-h3 text-foreground">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Đóng" className="flex size-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring">
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

function ConfirmSubmit({
  total,
  answered,
  flagged,
  submitting,
  onCancel,
  onConfirm,
  onReview,
}: {
  total: number;
  answered: number;
  flagged: number;
  submitting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onReview: () => void;
}) {
  const unanswered = total - answered;
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelector<HTMLButtonElement>('[data-primary]')?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !submitting && onCancel();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, submitting]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <motion.div className="absolute inset-0 bg-foreground/50 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => !submitting && onCancel()} />
      <motion.div
        ref={ref}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
        initial={{ opacity: 0, scale: 0.92, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 360, damping: 28 }}
        className="relative grid w-full max-w-md justify-items-center gap-4 rounded-[2rem] bg-background p-6 text-center shadow-lift"
      >
        <Image src={`/brand/mascot/static/${unanswered ? 'studying' : 'success'}.webp`} alt="" width={384} height={384} className="-mt-16 h-auto w-28 drop-shadow-mascot" />
        <h2 id="confirm-title" className="text-h2 text-foreground">
          {unanswered ? 'Nộp bài luôn nhé?' : 'Bạn đã làm hết rồi!'}
        </h2>
        <div id="confirm-desc" className="grid w-full grid-cols-3 gap-2">
          <div className="rounded-2xl bg-primary-subtle p-3">
            <p className="text-h2 font-bold text-primary tabular-nums">{answered}</p>
            <p className="text-caption text-muted-foreground">đã làm</p>
          </div>
          <div className={cn('rounded-2xl p-3', unanswered ? 'bg-danger-subtle' : 'bg-surface')}>
            <p className={cn('text-h2 font-bold tabular-nums', unanswered ? 'text-danger' : 'text-muted-foreground')}>{unanswered}</p>
            <p className="text-caption text-muted-foreground">còn trống</p>
          </div>
          <div className={cn('rounded-2xl p-3', flagged ? 'bg-warning-subtle' : 'bg-surface')}>
            <p className={cn('text-h2 font-bold tabular-nums', flagged ? 'text-warning' : 'text-muted-foreground')}>{flagged}</p>
            <p className="text-caption text-muted-foreground">đánh dấu</p>
          </div>
        </div>
        {(unanswered > 0 || flagged > 0) && <p className="text-body text-muted-foreground">Câu bỏ trống tính 0 điểm. Bạn còn thời gian để xem lại.</p>}
        <div className="grid w-full gap-2">
          <Button size="lg" fullWidth onClick={onConfirm} loading={submitting} data-primary leftIcon={<Send aria-hidden="true" />}>
            {submitting ? 'Đang chấm bài…' : 'Nộp bài'}
          </Button>
          {(unanswered > 0 || flagged > 0) && (
            <Button size="lg" variant="outline" fullWidth onClick={onReview} disabled={submitting}>
              Xem lại câu {unanswered ? 'còn trống' : 'đã đánh dấu'}
            </Button>
          )}
          <Button variant="ghost" fullWidth onClick={onCancel} disabled={submitting}>
            Làm tiếp
          </Button>
        </div>
      </motion.div>
    </div>
  );
}
