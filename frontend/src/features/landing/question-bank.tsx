'use client';

import { BadgeCheck } from 'lucide-react';
import { animate, motion, useInView, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { Container, Section, SectionHeader } from '@/components/layout/container';
import { Reveal, Stagger, StaggerItem } from '@/components/motion/reveal';
import { cn } from '@/lib/cn';
import { bankChapters, bankDifficulty, bankTotals, bankTypes, gradeTotals, type Grade } from './bank-data';

const ease = [0.22, 1, 0.36, 1] as const;
const fmt = new Intl.NumberFormat('vi-VN');
const GRADES: Grade[] = [10, 11, 12];
const MAX_COUNT = Math.max(...bankChapters.map((c) => c.count));

/* ---------- Số đếm chạy khi cuộn tới ---------- */

function CountUp({ to }: { to: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  const reduce = useReducedMotion();
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setValue(to);
      return;
    }
    const controls = animate(0, to, { duration: 1.4, ease, onUpdate: (v) => setValue(Math.round(v)) });
    return () => controls.stop();
  }, [inView, reduce, to]);

  return (
    <>
      <span className="sr-only">{fmt.format(to)}</span>
      <span ref={ref} aria-hidden="true">
        {fmt.format(value)}
      </span>
    </>
  );
}

const stats = [
  { value: bankTotals.questions, label: 'câu hỏi đã duyệt', suffix: '' },
  { value: bankTotals.chapters, label: 'chương, khối 10–12', suffix: '' },
  { value: bankTotals.subtopics, label: 'chuyên đề nhỏ', suffix: '' },
  { value: 4, label: 'mức độ khó', suffix: '' },
];

/* ---------- Biểu đồ cột ngang theo chương ---------- */

function ChapterChart() {
  const [grade, setGrade] = useState<Grade>(12);
  const rows = bankChapters.filter((c) => c.grade === grade);

  return (
    <div className="flex h-full flex-col rounded-3xl border border-primary-foreground/10 bg-primary-foreground/5 p-6 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-h3 text-primary-foreground">Số câu theo chương</h3>
          <p className="mt-1 text-caption text-primary-foreground/65">
            Khối {grade}: <strong className="text-primary-foreground tabular-nums">{fmt.format(gradeTotals[grade])}</strong>{' '}
            câu · {rows.length} chương
          </p>
        </div>
        <div role="tablist" aria-label="Chọn khối" className="flex gap-1 rounded-full bg-primary-foreground/10 p-1">
          {GRADES.map((g) => (
            <button
              key={g}
              type="button"
              role="tab"
              aria-selected={g === grade}
              onClick={() => setGrade(g)}
              className={cn(
                'rounded-full px-4 py-1.5 text-label font-semibold transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-2',
                g === grade
                  ? 'bg-accent text-foreground'
                  : 'text-primary-foreground/75 hover:bg-primary-foreground/10 hover:text-primary-foreground',
              )}
            >
              Lớp {g}
            </button>
          ))}
        </div>
      </div>

      <ul key={grade} className="mt-6 grid flex-1 content-evenly gap-3.5" aria-label={`Số câu theo chương, khối ${grade}`}>
        {rows.map((c, i) => (
          <li key={c.code} className="grid gap-1.5">
            <div className="flex items-baseline justify-between gap-3 text-label">
              <span className="min-w-0 truncate text-primary-foreground/90">
                <span className="mr-2 text-caption font-semibold text-accent tabular-nums">{c.code}</span>
                {c.name}
              </span>
              <span className="shrink-0 font-semibold text-primary-foreground tabular-nums">{fmt.format(c.count)}</span>
            </div>
            <span className="block h-2.5 overflow-hidden rounded-full bg-primary-foreground/10">
              <motion.span
                className="block h-full rounded-full bg-linear-to-r from-accent to-[#9be3f2]"
                initial={{ width: 0 }}
                animate={{ width: `${(c.count / MAX_COUNT) * 100}%` }}
                transition={{ delay: 0.05 + i * 0.05, duration: 0.8, ease }}
              />
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-5 text-caption text-primary-foreground/55">Mọi thanh dùng chung một thang, nên so sánh được giữa các khối.</p>
    </div>
  );
}

/* ---------- Thanh chồng theo mức độ ---------- */

function DifficultyChart() {
  const total = bankDifficulty.reduce((s, d) => s + d.count, 0);
  return (
    <div className="rounded-3xl border border-primary-foreground/10 bg-primary-foreground/5 p-6 sm:p-7">
      <h3 className="text-h3 text-primary-foreground">Phân bố mức độ</h3>
      <p className="mt-1 text-caption text-primary-foreground/65">Đủ bốn mức để cân đề vừa sức</p>

      <div className="mt-5 flex h-4 gap-1 overflow-hidden rounded-full" role="img" aria-label="Tỉ lệ bốn mức độ khó">
        {bankDifficulty.map((d, i) => (
          <motion.span
            key={d.code}
            className="h-full first:rounded-l-full last:rounded-r-full"
            style={{ backgroundColor: d.color }}
            initial={{ width: 0 }}
            whileInView={{ width: `${(d.count / total) * 100}%` }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 + i * 0.1, duration: 0.9, ease }}
          />
        ))}
      </div>

      <ul className="mt-5 grid grid-cols-2 gap-3">
        {bankDifficulty.map((d) => (
          <li key={d.code} className="rounded-2xl bg-primary-foreground/5 px-3.5 py-3">
            <span className="flex items-center gap-2 text-caption text-primary-foreground/75">
              <span className="size-2.5 rounded-full" style={{ backgroundColor: d.color }} aria-hidden="true" />
              {d.code} · {d.name}
            </span>
            <span className="mt-1 flex items-baseline gap-1.5">
              <span className="text-h2 font-bold text-primary-foreground tabular-nums">{fmt.format(d.count)}</span>
              <span className="text-caption text-primary-foreground/60 tabular-nums">{Math.round((d.count / total) * 100)}%</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ---------- Biểu đồ vành khuyên theo dạng câu ---------- */

const R = 40;
const C = 2 * Math.PI * R;

function TypeDonut() {
  const total = bankTypes.reduce((s, t) => s + t.count, 0);
  let offset = 0;
  return (
    <div className="rounded-3xl border border-primary-foreground/10 bg-primary-foreground/5 p-6 sm:p-7">
      <h3 className="text-h3 text-primary-foreground">Ba dạng câu hỏi</h3>
      <p className="mt-1 text-caption text-primary-foreground/65">Giống cấu trúc đề thi THPT hiện hành</p>

      <div className="mt-5 flex items-center gap-6">
        <svg viewBox="0 0 100 100" className="size-32 shrink-0 -rotate-90" role="img" aria-label="Tỉ lệ ba dạng câu hỏi">
          <circle cx="50" cy="50" r={R} fill="none" stroke="currentColor" strokeWidth="14" className="text-primary-foreground/10" />
          {bankTypes.map((t, i) => {
            const len = (t.count / total) * C;
            const start = offset;
            offset += len;
            return (
              <motion.circle
                key={t.code}
                cx="50"
                cy="50"
                r={R}
                fill="none"
                stroke={t.color}
                strokeWidth="14"
                strokeDashoffset={-start}
                initial={{ strokeDasharray: `0 ${C}` }}
                whileInView={{ strokeDasharray: `${Math.max(len - 1.5, 0)} ${C}` }}
                viewport={{ once: true }}
                transition={{ delay: 0.15 + i * 0.2, duration: 0.9, ease }}
              />
            );
          })}
        </svg>
        <ul className="grid flex-1 gap-3">
          {bankTypes.map((t) => (
            <li key={t.code} className="grid gap-0.5">
              <span className="flex items-center gap-2 text-caption text-primary-foreground/75">
                <span className="size-2.5 rounded-full" style={{ backgroundColor: t.color }} aria-hidden="true" />
                {t.name}
              </span>
              <span className="flex items-baseline gap-1.5">
                <span className="text-h3 font-bold text-primary-foreground tabular-nums">{fmt.format(t.count)}</span>
                <span className="text-caption text-primary-foreground/60 tabular-nums">{Math.round((t.count / total) * 100)}%</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function QuestionBank() {
  return (
    <Section id="ngan-hang" tone="inverse" aria-labelledby="ngan-hang-title" className="overflow-hidden">
      <div className="bg-grid-inverse mask-fade pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-40 -left-32 size-[520px] rounded-full bg-accent/15 blur-3xl" aria-hidden="true" />
      <Container className="relative">
        <Reveal>
          <SectionHeader
            inverse
            titleId="ngan-hang-title"
            eyebrow="Kho câu hỏi"
            title={
              <>
                Hơn {fmt.format(1200)} câu đã duyệt, phủ {bankTotals.chapters} chương Toán 10–12
              </>
            }
            description="Mỗi câu đều có chương, chuyên đề và mức độ rõ ràng, nên Examind chọn đúng chỗ bạn cần thay vì bốc ngẫu nhiên cả đề."
          />
        </Reveal>

        <Stagger className="mt-12 grid grid-cols-2 gap-3 lg:grid-cols-4" stagger={0.08}>
          {stats.map((s) => (
            <StaggerItem key={s.label}>
              <div className="h-full rounded-3xl border border-primary-foreground/10 bg-primary-foreground/5 px-5 py-6 text-center">
                <p className="text-display font-bold tracking-tight text-primary-foreground tabular-nums">
                  <CountUp to={s.value} />
                </p>
                <p className="mt-1 text-label text-primary-foreground/70">{s.label}</p>
              </div>
            </StaggerItem>
          ))}
        </Stagger>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
          <Reveal className="h-full">
            <ChapterChart />
          </Reveal>
          <div className="grid content-start gap-5">
            <Reveal delay={0.1}>
              <DifficultyChart />
            </Reveal>
            <Reveal delay={0.2}>
              <TypeDonut />
            </Reveal>
          </div>
        </div>

        <Reveal delay={0.1}>
          <p className="mx-auto mt-8 flex max-w-2xl items-start justify-center gap-2 text-center text-caption text-primary-foreground/60">
            <BadgeCheck className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden="true" />
            Số liệu của ngân hàng mẫu dùng trong bản chạy thử. Toàn bộ {fmt.format(bankTotals.questions)} câu đều đã duyệt; một câu
            thuộc hai chương nên không tính vào tổng theo khối.
          </p>
        </Reveal>
      </Container>
    </Section>
  );
}
