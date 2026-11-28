'use client';

import {
  Dices,
  FileImage,
  Layers,
  RotateCcw,
  SlidersHorizontal,
  Target,
  type LucideIcon,
} from 'lucide-react';
import Image from 'next/image';
import { AnimatePresence, motion } from 'motion/react';
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Container, Section, SectionHeader } from '@/components/layout/container';
import { Reveal } from '@/components/motion/reveal';
import { Badge } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';

/* ---------- Hình minh hoạ trong từng tình huống ---------- */

const ease = [0.22, 1, 0.36, 1] as const;

function Bar({ value, className, delay = 0 }: { value: number; className?: string; delay?: number }) {
  return (
    <span className="block h-2 overflow-hidden rounded-full bg-surface-muted">
      <motion.span
        className={cn('block h-full rounded-full', className)}
        initial={{ width: 0 }}
        animate={{ width: `${value * 100}%` }}
        transition={{ delay: 0.15 + delay, duration: 0.7, ease }}
      />
    </span>
  );
}

const weakRows = [
  { name: 'Ứng dụng đạo hàm', wrong: 7, total: 12, tone: 'bg-danger' },
  { name: 'Nguyên hàm và tích phân', wrong: 4, total: 10, tone: 'bg-warning' },
  { name: 'Toạ độ trong không gian', wrong: 2, total: 9, tone: 'bg-success' },
];

function WeakChapters() {
  return (
    <div className="mt-3 grid gap-3 rounded-xl border border-border bg-background p-3.5">
      {weakRows.map((r, i) => (
        <div key={r.name} className="grid gap-1.5">
          <div className="flex justify-between gap-3 text-caption">
            <span className="text-foreground">{r.name}</span>
            <span className="shrink-0 font-semibold text-muted-foreground tabular-nums">
              {r.wrong}/{r.total} câu sai
            </span>
          </div>
          <Bar value={r.wrong / r.total} className={r.tone} delay={i * 0.1} />
        </div>
      ))}
    </div>
  );
}

const wrongList = [
  { chapter: 'Ứng dụng đạo hàm', level: 'VD', times: 3 },
  { chapter: 'Nguyên hàm và tích phân', level: 'TH', times: 2 },
  { chapter: 'Hàm số mũ và lôgarit', level: 'VD', times: 2 },
  { chapter: 'Toạ độ trong không gian', level: 'NB', times: 1 },
];

function WrongQuestions() {
  return (
    <div className="mt-3 grid gap-2 rounded-xl border border-border bg-background p-3.5">
      {wrongList.map((q, i) => (
        <motion.div
          key={q.chapter}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 + i * 0.08, duration: 0.45, ease }}
          className="flex items-center gap-2.5 text-caption"
        >
          <span className="w-9 shrink-0 rounded-md bg-primary-subtle py-0.5 text-center font-semibold text-primary">
            {q.level}
          </span>
          <span className="flex-1 truncate text-foreground">{q.chapter}</span>
          <span
            className={cn(
              'shrink-0 rounded-full px-2 py-0.5 font-semibold tabular-nums',
              q.times >= 2 ? 'bg-danger-subtle text-danger' : 'bg-surface-muted text-muted-foreground',
            )}
          >
            Sai {q.times} lần
          </span>
        </motion.div>
      ))}
    </div>
  );
}

/** 48 ô = 48 câu của một chương. Ô đã làm mờ đi, ô được chọn cho đề sáng lên. Sắp xếp cố định để không lệch khi SSR. */
const picked = new Set([3, 8, 11, 15, 19, 24, 29, 34, 38, 44]);
const done = new Set([0, 1, 2, 4, 5, 7, 9, 12, 13, 16, 17, 20, 21, 22, 25, 26, 28, 30, 31, 33, 35, 36, 40, 41, 43, 46]);

function NoRepeat() {
  return (
    <div className="mt-3 rounded-xl border border-border bg-background p-3.5">
      <div className="grid grid-cols-12 gap-1.5" aria-hidden="true">
        {Array.from({ length: 48 }, (_, i) => {
          const isPicked = picked.has(i);
          const isDone = done.has(i);
          return (
            <motion.span
              key={i}
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.05 + i * 0.012, duration: 0.35, ease }}
              className={cn(
                'aspect-square rounded-md',
                isPicked && 'bg-accent shadow-glow',
                !isPicked && isDone && 'bg-surface-muted',
                !isPicked && !isDone && 'border border-border bg-background',
              )}
            />
          );
        })}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-caption text-muted-foreground">
        <li className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-surface-muted" aria-hidden="true" /> Đã làm (loại ra)
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm border border-border" aria-hidden="true" /> Chưa làm
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-accent" aria-hidden="true" /> Chọn cho đề này
        </li>
      </ul>
    </div>
  );
}

const matrixRows = [
  { name: 'Ứng dụng đạo hàm', cells: [2, 3, 2, 1] },
  { name: 'Nguyên hàm, tích phân', cells: [1, 2, 2, 1] },
  { name: 'Toạ độ trong không gian', cells: [1, 2, 1, 0] },
  { name: 'Xác suất có điều kiện', cells: [1, 1, 1, 0] },
];
const matrixHead = ['NB', 'TH', 'VD', 'VDC'];
const heat = ['bg-surface text-muted-foreground', 'bg-accent-subtle text-accent-strong', 'bg-accent/30 text-foreground', 'bg-accent text-foreground'];

function ExamMatrix() {
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-border bg-background text-caption">
      <div className="grid grid-cols-[1fr_repeat(4,2.25rem)] gap-1 bg-surface px-3 py-2 font-semibold text-muted-foreground">
        <span>Chương</span>
        {matrixHead.map((h) => (
          <span key={h} className="text-center">
            {h}
          </span>
        ))}
      </div>
      {matrixRows.map((r, ri) => (
        <div key={r.name} className="grid grid-cols-[1fr_repeat(4,2.25rem)] items-center gap-1 border-t border-border px-3 py-1.5">
          <span className="truncate text-foreground">{r.name}</span>
          {r.cells.map((n, ci) => (
            <motion.span
              key={ci}
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + (ri * 4 + ci) * 0.03, duration: 0.35, ease }}
              className={cn('rounded-md py-1 text-center font-semibold tabular-nums', heat[Math.min(n, 3)])}
            >
              {n || '–'}
            </motion.span>
          ))}
        </div>
      ))}
    </div>
  );
}

function ImageMatrix() {
  return (
    <div className="mt-3 grid gap-3 rounded-xl border border-border bg-background p-3.5 sm:grid-cols-[auto_1fr]">
      <motion.div
        initial={{ opacity: 0, rotate: -3, scale: 0.9 }}
        animate={{ opacity: 1, rotate: -2, scale: 1 }}
        transition={{ duration: 0.5, ease }}
        className="relative mx-auto grid h-24 w-32 content-center gap-1.5 overflow-hidden rounded-lg border border-border bg-surface p-2.5 shadow-soft sm:mx-0"
        aria-hidden="true"
      >
        {Array.from({ length: 5 }, (_, r) => (
          <div key={r} className="grid grid-cols-5 gap-1">
            {Array.from({ length: 5 }, (_, c) => (
              <span key={c} className={cn('h-2.5 rounded-[3px]', r === 0 || c === 0 ? 'bg-primary/25' : 'bg-primary/10')} />
            ))}
          </div>
        ))}
        <motion.span
          className="absolute inset-x-0 h-0.5 bg-accent shadow-glow"
          initial={{ top: '8%' }}
          animate={{ top: ['8%', '92%', '8%'] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      </motion.div>
      <div className="grid content-center gap-2 text-caption">
        <span className="flex items-center gap-1.5 font-semibold text-foreground">
          <FileImage className="size-3.5 text-accent-strong" aria-hidden="true" /> ma-tran-de.jpg
        </span>
        <p className="text-muted-foreground">Đọc được ma trận, đối chiếu với các chương trong ngân hàng:</p>
        <div className="flex flex-wrap gap-1.5">
          {['12C1 · 6 câu', '12C4 · 4 câu', '12C5 · 3 câu', '12C6 · 2 câu'].map((t, i) => (
            <motion.span
              key={t}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1, duration: 0.4, ease }}
              className="rounded-full bg-primary-subtle px-2.5 py-1 font-semibold text-primary tabular-nums"
            >
              {t}
            </motion.span>
          ))}
        </div>
      </div>
    </div>
  );
}

const editRows = [
  { code: 'NB', before: 3, after: 3 },
  { code: 'TH', before: 4, after: 6 },
  { code: 'VD', before: 2, after: 1 },
  { code: 'VDC', before: 1, after: 0 },
];

function EditExam() {
  return (
    <div className="mt-3 grid gap-2 rounded-xl border border-border bg-background p-3.5">
      {editRows.map((r, i) => {
        const diff = r.after - r.before;
        return (
          <div key={r.code} className="grid grid-cols-[2.5rem_1fr_3.25rem] items-center gap-2 text-caption">
            <span className="font-semibold text-muted-foreground">{r.code}</span>
            <span className="relative block h-2 overflow-hidden rounded-full bg-surface-muted">
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-border"
                style={{ width: `${(r.before / 6) * 100}%` }}
              />
              <motion.span
                className="absolute inset-y-0 left-0 rounded-full bg-linear-to-r from-primary to-accent"
                initial={{ width: `${(r.before / 6) * 100}%` }}
                animate={{ width: `${(r.after / 6) * 100}%` }}
                transition={{ delay: 0.5 + i * 0.1, duration: 0.8, ease }}
              />
            </span>
            <span
              className={cn(
                'text-right font-semibold tabular-nums',
                diff > 0 && 'text-success',
                diff < 0 && 'text-danger',
                diff === 0 && 'text-muted-foreground',
              )}
            >
              {r.before}→{r.after}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Danh sách tình huống ---------- */

interface Capability {
  id: string;
  icon: LucideIcon;
  title: string;
  short: string;
  ask: string;
  reply: ReactNode;
  visual: ReactNode;
}

const capabilities: Capability[] = [
  {
    id: 'chuong-yeu',
    icon: Target,
    title: 'Ôn đúng chương hay sai',
    short: 'Đọc lịch sử làm bài, chỉ ra chương mất điểm nhiều nhất kèm số liệu.',
    ask: 'Ôn giúp mình phần mình hay sai nhé.',
    reply: (
      <>
        Qua các lần làm gần nhất, bạn sai nhiều nhất ở <strong className="text-primary">Ứng dụng đạo hàm</strong>. Mình
        đề xuất tập trung vào ba chương này:
      </>
    ),
    visual: <WeakChapters />,
  },
  {
    id: 'cau-sai',
    icon: RotateCcw,
    title: 'Làm lại đúng các câu đã sai',
    short: 'Gom câu từng sai, ưu tiên câu sai nhiều lần để luyện lại.',
    ask: 'Cho mình làm lại các câu đã sai.',
    reply: <>Bạn có 4 chương còn câu sai chưa làm lại. Mình ưu tiên câu sai nhiều lần trước:</>,
    visual: <WrongQuestions />,
  },
  {
    id: 'on-tiep',
    icon: Dices,
    title: 'Ôn tiếp, không lặp câu cũ',
    short: 'Chọn ngẫu nhiên từ các câu chưa làm, bù bằng câu thật khi ô thiếu.',
    ask: 'Tạo đề ôn tiếp 10 câu.',
    reply: (
      <>
        Mình bỏ qua <strong className="text-primary">26 câu bạn đã làm</strong> và chọn ngẫu nhiên 10 câu mới từ phần
        còn lại của chương:
      </>
    ),
    visual: <NoRepeat />,
  },
  {
    id: 'ky-thi',
    icon: Layers,
    title: 'Ra đề theo cấu trúc kỳ thi',
    short: 'Nêu kỳ thi và khối lớp, Examind dựng ma trận chương × mức độ.',
    ask: 'Ra đề theo cấu trúc thi học kỳ 1 lớp 12.',
    reply: <>Đây là ma trận đề đề xuất, gồm 21 câu. Bạn xem rồi chỉnh trước khi mình ghép đề:</>,
    visual: <ExamMatrix />,
  },
  {
    id: 'gui-anh',
    icon: FileImage,
    title: 'Gửi ảnh ma trận hoặc bài muốn ôn',
    short: 'Chụp ma trận đề hay dạng bài, Examind gợi ý chương và ra đề luyện. Không giải hộ.',
    ask: 'Mình gửi ảnh ma trận đề của cô, ra đề luyện giống vậy nhé.',
    reply: <>Mình đọc xong ma trận. Mình không giải bài, nhưng sẽ ra đề luyện đúng các chương này:</>,
    visual: <ImageMatrix />,
  },
  {
    id: 'chinh-de',
    icon: SlidersHorizontal,
    title: 'Chỉnh đề bằng một câu nói',
    short: 'Đổi số câu, mức độ hay chương bằng lời. Chỉ ghép đề khi bạn xác nhận.',
    ask: 'Bớt câu vận dụng cao, thêm 2 câu thông hiểu.',
    reply: <>Mình giữ tổng 10 câu nên bớt thêm 1 câu vận dụng. Bạn xác nhận thì mình ghép đề nháp:</>,
    visual: <EditExam />,
  },
];

/* ---------- Khung chat ---------- */

function CapabilityPanel({ item }: { item: Capability }) {
  return (
    <div className="overflow-hidden rounded-[28px] border border-border bg-background shadow-lift">
      <div className="flex items-center gap-3 border-b border-border px-5 py-3.5">
        <Image src="/brand/examind-mark.png" alt="" width={36} height={36} className="size-9" />
        <div className="grid flex-1">
          <span className="text-label font-semibold text-foreground">Examind</span>
          <span className="flex items-center gap-1.5 text-caption text-muted-foreground">
            <span className="size-1.5 rounded-full bg-success" aria-hidden="true" />
            Trợ lý ôn Toán
          </span>
        </div>
        <Badge tone="accent">Minh hoạ</Badge>
      </div>

      <div className="grid min-h-[400px] content-start gap-3 bg-[radial-gradient(circle_at_top,var(--color-surface),var(--color-background)_70%)] p-4 sm:p-5">
        <AnimatePresence mode="wait">
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease }}
            className="grid gap-3"
          >
            <div className="flex justify-end">
              <p className="max-w-[88%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-label text-primary-foreground">
                {item.ask}
              </p>
            </div>
            <div className="flex">
              <div className="max-w-[94%] rounded-2xl rounded-bl-md border border-border bg-surface px-4 py-3 text-label leading-relaxed text-foreground">
                <p>{item.reply}</p>
                {item.visual}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export function AgentCapabilities() {
  const [active, setActive] = useState(capabilities[0].id);
  const baseId = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const current = capabilities.find((c) => c.id === active) ?? capabilities[0];

  function onKeyDown(e: KeyboardEvent, index: number) {
    const step = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? -1 : 0;
    if (!step && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const next =
      e.key === 'Home' ? 0 : e.key === 'End' ? capabilities.length - 1 : (index + step + capabilities.length) % capabilities.length;
    setActive(capabilities[next].id);
    refs.current[next]?.focus();
  }

  return (
    <Section id="chuc-nang" aria-labelledby="chuc-nang-title">
      <Container>
        <Reveal>
          <SectionHeader
            titleId="chuc-nang-title"
            eyebrow="Agent làm được gì"
            title="Sáu cách ôn, chỉ cần nhắn một câu"
            description="Chọn một tình huống để xem Examind trả lời ra sao. Mọi đề đều qua bước xem trước và chỉ ghép từ câu đã duyệt."
          />
        </Reveal>

        <div className="mt-14 grid items-start gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:gap-12">
          <Reveal>
            <div role="tablist" aria-label="Chức năng của agent" aria-orientation="vertical" className="grid gap-2.5">
              {capabilities.map(({ id, icon: Icon, title, short }, i) => {
                const selected = id === active;
                return (
                  <button
                    key={id}
                    ref={(el) => {
                      refs.current[i] = el;
                    }}
                    type="button"
                    role="tab"
                    id={`${baseId}-tab-${id}`}
                    aria-selected={selected}
                    aria-controls={`${baseId}-panel`}
                    tabIndex={selected ? 0 : -1}
                    onClick={() => setActive(id)}
                    onKeyDown={(e) => onKeyDown(e, i)}
                    className={cn(
                      'group flex items-start gap-4 rounded-2xl border p-4 text-left transition-[background-color,border-color,box-shadow,translate] duration-300 focus-visible:outline-2 focus-visible:outline-offset-2',
                      selected
                        ? 'border-primary/30 bg-background shadow-lift lg:translate-x-1'
                        : 'border-transparent hover:border-border hover:bg-surface',
                    )}
                  >
                    <span
                      className={cn(
                        'flex size-11 shrink-0 items-center justify-center rounded-2xl transition-colors duration-300',
                        selected
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-primary-subtle text-primary group-hover:bg-primary/15',
                      )}
                    >
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="grid gap-0.5">
                      <span className="text-body font-semibold text-foreground">{title}</span>
                      <span className="text-label font-normal text-muted-foreground">{short}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </Reveal>

          <Reveal delay={0.1} className="lg:sticky lg:top-24">
            <div id={`${baseId}-panel`} role="tabpanel" aria-labelledby={`${baseId}-tab-${current.id}`} tabIndex={0}>
              <CapabilityPanel item={current} />
            </div>
            <p className="mt-3 text-center text-caption text-muted-foreground">
              Giao diện minh hoạ, số liệu chỉ là ví dụ.
            </p>
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}
