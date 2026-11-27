'use client';

import { CircleCheck, FileText, SendHorizontal, SlidersHorizontal } from 'lucide-react';
import Image from 'next/image';
import { AnimatePresence, motion, useInView, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { Badge } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';

/** Thời gian (ms) giữ mỗi bước trước khi sang bước sau. Bước cuối giữ lâu rồi lặp lại. */
const STAGE_MS = [700, 1500, 2000, 2400, 4200];
const FINAL = STAGE_MS.length - 1;

const structure = [
  { code: 'NB', count: 3 },
  { code: 'TH', count: 4 },
  { code: 'VD', count: 2 },
  { code: 'VDC', count: 1 },
];

function Bubble({ from, children }: { from: 'student' | 'examind'; children: ReactNode }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      className={cn('flex', from === 'student' ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[88%] rounded-2xl px-4 py-3 text-label leading-relaxed',
          from === 'student'
            ? 'rounded-br-md bg-primary text-primary-foreground'
            : 'rounded-bl-md border border-border bg-surface text-foreground',
        )}
      >
        {children}
      </div>
    </motion.div>
  );
}

export function ChatDemo() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const [stage, setStage] = useState(0);
  const shown = reduce ? FINAL : stage;

  useEffect(() => {
    if (reduce || !inView) return;
    const timer = window.setTimeout(() => setStage((s) => (s >= FINAL ? 0 : s + 1)), STAGE_MS[stage]);
    return () => window.clearTimeout(timer);
  }, [stage, reduce, inView]);

  return (
    <figure ref={ref} className="relative">
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

        <div className="flex h-[400px] flex-col justify-end gap-3 overflow-hidden bg-[radial-gradient(circle_at_top,var(--color-surface),var(--color-background)_70%)] p-4 sm:h-[420px] sm:p-5">
          <AnimatePresence mode="popLayout">
            {shown >= 1 && (
              <Bubble key="ask" from="student">
                Tuần sau kiểm tra 1 tiết, mình hay sai phần đạo hàm. Ra giúp mình đề ôn nhé!
              </Bubble>
            )}

            {shown === 2 && (
              <motion.div
                key="thinking"
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex items-center gap-2 text-caption font-medium text-muted-foreground"
              >
                <MascotAnimation motion="thinking" size={44} />
                Examind đang xem lịch sử làm bài…
              </motion.div>
            )}

            {shown >= 3 && (
              <Bubble key="preview" from="examind">
                <p>
                  Bạn sai nhiều nhất ở <strong className="font-semibold text-primary">Ứng dụng đạo hàm</strong>: 7/12 câu
                  gần nhất. Mình đề xuất đề 10 câu:
                </p>
                <div className="mt-3 grid gap-2 rounded-xl border border-border bg-background p-3">
                  {structure.map((row, i) => (
                    <div key={row.code} className="grid grid-cols-[2.5rem_1fr_1.5rem] items-center gap-2 text-caption">
                      <span className="font-semibold text-muted-foreground">{row.code}</span>
                      <span className="h-2 overflow-hidden rounded-full bg-surface-muted">
                        <motion.span
                          className="block h-full rounded-full bg-linear-to-r from-primary to-accent"
                          initial={{ width: 0 }}
                          animate={{ width: `${(row.count / 4) * 100}%` }}
                          transition={{ delay: 0.25 + i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                        />
                      </span>
                      <span className="text-right font-semibold tabular-nums">{row.count}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-2" aria-hidden="true">
                  <span className="inline-flex items-center gap-1.5 rounded-lg border border-input px-3 py-1.5 text-caption font-semibold">
                    <SlidersHorizontal className="size-3.5" /> Chỉnh
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-caption font-semibold transition-colors duration-300',
                      shown >= 4 ? 'bg-success text-primary-foreground' : 'bg-primary text-primary-foreground',
                    )}
                  >
                    <CircleCheck className="size-3.5" /> {shown >= 4 ? 'Đã xác nhận' : 'Xác nhận'}
                  </span>
                </div>
              </Bubble>
            )}

            {shown >= 4 && (
              <Bubble key="draft" from="examind">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-subtle text-accent-strong">
                    <FileText className="size-5" aria-hidden="true" />
                  </span>
                  <div className="grid">
                    <span className="font-semibold">Đề nháp: 10 câu đã duyệt</span>
                    <span className="text-caption text-muted-foreground">Không kèm đáp án · sẵn sàng để in</span>
                  </div>
                </div>
              </Bubble>
            )}
          </AnimatePresence>
        </div>

        <div className="flex items-center gap-2 border-t border-border p-3" aria-hidden="true">
          <span className="flex h-11 flex-1 items-center rounded-xl bg-surface px-4 text-label text-muted-foreground">
            Nhắn yêu cầu ôn…
          </span>
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <SendHorizontal className="size-5" />
          </span>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-caption text-muted-foreground">
        Giao diện minh hoạ, số liệu chỉ là ví dụ.
      </figcaption>
    </figure>
  );
}
