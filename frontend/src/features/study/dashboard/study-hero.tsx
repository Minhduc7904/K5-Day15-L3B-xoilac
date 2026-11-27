'use client';

import { ArrowRight, Sparkles } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, type FormEvent, type ReactNode } from 'react';
import { formatScore } from '../grading';
import type { DashboardData } from '../types';
import { CountUp } from './count-up';
import { StudyStreak } from './streak-card';

const suggestions = ['Ôn chương mình hay sai', 'Đề tích phân 20 phút', 'Hình không gian cơ bản', 'Mũ – lôgarit 15 phút'];
const TARGET = 8;
const ease = [0.16, 1, 0.3, 1] as const;

type Props = { name: string; data: DashboardData };

/**
 * Đầu trang tổng quan: linh vật kể lại số liệu học tập bằng một câu nói (thay cho hàng 4 ô số),
 * ô tạo đề nhanh, và chuỗi ngày học ở cột phải.
 */
export function StudyHero({ name, data }: Props) {
  const reduce = useReducedMotion();
  const studiedToday = data.streak.days.at(-1)?.studied ?? false;
  const pose = data.totals.exams === 0 ? 'welcome' : studiedToday ? 'success' : 'studying';

  return (
    <section
      aria-labelledby="hero-title"
      className="relative isolate overflow-hidden rounded-3xl bg-primary text-primary-foreground shadow-lift"
    >
      <div aria-hidden="true" className="bg-grid-inverse absolute inset-0 -z-10 [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" />
      <div className="grid gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,1fr)_19rem] lg:gap-0 lg:p-0">
        <div className="grid gap-5 lg:p-8 xl:p-10">
          <div className="grid grid-cols-[auto_minmax(0,1fr)] items-end gap-3 sm:gap-5">
            <motion.div
              className="relative w-24 sm:w-36 xl:w-44"
              initial={reduce ? false : { opacity: 0, y: 24, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.7, ease }}
            >
              <motion.div
                animate={reduce ? undefined : { y: [0, -6, 0] }}
                transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}
                whileHover={reduce ? undefined : { rotate: [0, -6, 5, -3, 0], transition: { duration: 0.6 } }}
              >
                <Image
                  src={`/brand/mascot/static/${pose}.webp`}
                  alt=""
                  width={192}
                  height={192}
                  priority
                  unoptimized
                  className="pixelated h-auto w-full drop-shadow-[0_10px_14px_rgb(3_23_47/0.45)]"
                />
              </motion.div>
              <span aria-hidden="true" className="absolute inset-x-4 -bottom-1 h-2 rounded-full bg-foreground/35 blur-[3px]" />
            </motion.div>

            <motion.div
              className="relative mb-8 max-w-xl rounded-2xl rounded-bl-sm bg-background px-4 py-3.5 text-foreground shadow-soft sm:mb-14 sm:px-5 sm:py-4"
              initial={reduce ? false : { opacity: 0, scale: 0.92, x: -8 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              transition={{ duration: 0.55, delay: 0.25, ease }}
              style={{ originX: 0, originY: 1 }}
            >
              <svg aria-hidden="true" viewBox="0 0 14 14" className="absolute -left-[11px] bottom-0 size-3.5 fill-background">
                <path d="M14 0v14H0C7 12 12 7 14 0z" />
              </svg>
              <h1 id="hero-title" className="text-h3 text-balance">Chào {name}!</h1>
              <p className="mt-1 text-label leading-relaxed text-muted-foreground sm:text-body">
                <Recap totals={data.totals} />
              </p>
            </motion.div>
          </div>

          <QuickCreate weakest={data.chapters[0]?.chapter.name} />
        </div>

        <StudyStreak streak={data.streak} />
      </div>
    </section>
  );
}

/** Đánh dấu số như bút dạ quang trên vở. */
function Mark({ children }: { children: ReactNode }) {
  return (
    <strong className="rounded-[3px] bg-[linear-gradient(transparent_58%,color-mix(in_oklab,var(--color-ember)_55%,transparent)_58%)] px-0.5 font-bold whitespace-nowrap text-foreground">
      {children}
    </strong>
  );
}

function Recap({ totals }: { totals: DashboardData['totals'] }) {
  if (totals.exams === 0) {
    return <>Mình sẽ cùng bạn ôn Toán mỗi ngày. Gõ chủ đề bên dưới để làm đề đầu tiên nhé.</>;
  }

  const hours = Math.floor(totals.minutes / 60);
  const average = totals.average === null ? null : Math.round(totals.average * 100) / 100;
  const gap = average === null ? null : Math.round((TARGET - average) * 100) / 100;

  return (
    <>
      Bạn đã làm <Mark><CountUp value={totals.exams} delay={0.5} /> đề</Mark> với{' '}
      <Mark><CountUp value={totals.questions} delay={0.6} /> câu</Mark>, học tổng cộng{' '}
      <Mark>
        {hours > 0 && <><CountUp value={hours} delay={0.7} /> giờ </>}
        <CountUp value={totals.minutes % 60} delay={0.7} /> phút
      </Mark>
      .{' '}
      {average !== null && gap !== null && (
        <>
          Điểm trung bình đang là <Mark><CountUp value={average} decimals={2} delay={0.8} format={formatScore} /></Mark>
          {gap <= 0 ? <>, vượt mục tiêu {TARGET} điểm rồi đó!</> : <>, còn {formatScore(gap)} điểm nữa là chạm mục tiêu {TARGET}.</>}
        </>
      )}
    </>
  );
}

function QuickCreate({ weakest }: { weakest?: string }) {
  const router = useRouter();
  const [text, setText] = useState('');

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(`/exams/new?q=${encodeURIComponent(text.trim() || suggestions[0])}`);
  }

  return (
    <div className="grid min-w-0 gap-3">
      <h2 className="text-h3 text-primary-foreground">
        Hôm nay ôn gì?
        {weakest && (
          <span className="mt-0.5 block text-label font-normal text-primary-foreground/80">
            Mình gợi ý chương <strong className="font-semibold text-primary-foreground">{weakest}</strong>, chỗ bạn hay sai nhất.
          </span>
        )}
      </h2>
      <form
        onSubmit={submit}
        className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-2xl sm:grid-cols-[auto_minmax(0,1fr)_auto] bg-background p-1.5 shadow-soft transition-shadow focus-within:shadow-[0_0_0_4px_color-mix(in_oklab,var(--color-accent)_55%,transparent)]"
      >
        <label htmlFor="quick-prompt" className="sr-only">Yêu cầu tạo đề</label>
        <Sparkles aria-hidden="true" className="ml-2 hidden size-5 text-accent sm:block" />
        <input
          id="quick-prompt"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Ví dụ: Đề tích phân 30 phút"
          className="h-11 min-w-0 bg-transparent px-2.5 text-base text-foreground caret-accent outline-none placeholder:text-muted-foreground sm:pl-1"
        />
        <button
          type="submit"
          className="group inline-flex h-11 items-center gap-1.5 rounded-xl bg-flame-strong px-4 text-label font-semibold whitespace-nowrap text-primary-foreground transition-[background-color,transform] hover:bg-danger-hover active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Tạo đề
          <ArrowRight aria-hidden="true" className="size-4 transition-transform group-hover:translate-x-0.5" />
        </button>
      </form>
      <ul className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0" aria-label="Gợi ý nhanh">
        {suggestions.map((suggestion) => (
          <li key={suggestion}>
            <Link
              href={`/exams/new?q=${encodeURIComponent(suggestion)}`}
              className="inline-flex min-h-9 items-center whitespace-nowrap rounded-full border border-primary-foreground/25 px-3 text-caption font-medium text-primary-foreground transition-colors hover:border-primary-foreground/60 hover:bg-primary-foreground/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {suggestion}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
