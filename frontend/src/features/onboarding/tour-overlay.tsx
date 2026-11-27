'use client';

import { motion, useReducedMotion } from 'motion/react';
import { useEffect, useId, useRef, useState, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/cn';
import type { TourStep } from './steps';
import { TourBubble } from './tour-bubble';
import { MASCOT_SOURCES, TourMascot, type MascotLook } from './tour-mascot';
import { useTourTarget, type TargetRect } from './use-tour-target';

const MARGIN = 12;
const GAP = 16;
/** Khoảng đệm quanh phần tử được khoét sáng. */
const PAD = 8;
/** Quãng đường (px) từ đó linh vật chuyển sang dáng chạy. */
const RUN_DISTANCE = 160;
const SHEET_MAX = 640;
const COMPACT_MAX = 1023;

const spring = { type: 'spring', stiffness: 130, damping: 22, mass: 0.9 } as const;
const instant = { duration: 0 } as const;

interface Box {
  x: number;
  y: number;
}

/** Kích thước vùng nhìn thấy được, đo trên chính lớp phủ (đã trừ phần thanh cuộn được giữ chỗ). */
function useViewport(ref: RefObject<HTMLElement | null>) {
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return size;
}

/** Chỗ đặt thẻ nói: ưu tiên dưới, rồi trên, phải, trái phần tử; hết chỗ thì đặt ở góc dưới phải. */
function place(rect: TargetRect | null, group: { w: number; h: number }, view: { w: number; h: number }, sheet: boolean, top: number): Box {
  if (sheet) {
    const bottom = view.h - group.h - MARGIN;
    if (!rect) return { x: MARGIN, y: Math.max(top, (view.h - group.h) / 2) };
    return { x: MARGIN, y: rect.y + rect.h / 2 > view.h / 2 ? top + MARGIN : bottom };
  }
  if (!rect) return { x: (view.w - group.w) / 2, y: (view.h - group.h) / 2 };
  const clampX = (x: number) => Math.min(Math.max(x, MARGIN), view.w - group.w - MARGIN);
  const clampY = (y: number) => Math.min(Math.max(y, MARGIN), view.h - group.h - MARGIN);
  const below = rect.y + rect.h + GAP;
  if (below + group.h <= view.h - MARGIN) return { x: clampX(rect.x), y: below };
  const above = rect.y - GAP - group.h;
  if (above >= MARGIN) return { x: clampX(rect.x), y: above };
  const right = rect.x + rect.w + GAP;
  if (right + group.w <= view.w - MARGIN) return { x: right, y: clampY(rect.y) };
  const left = rect.x - GAP - group.w;
  if (left >= MARGIN) return { x: left, y: clampY(rect.y) };
  return { x: view.w - group.w - MARGIN, y: view.h - group.h - MARGIN };
}

export interface TourOverlayProps {
  step: TourStep;
  name: string;
  chapters: ReadonlyArray<{ id: string; label: string }>;
  first: boolean;
  last: boolean;
  /** Đã đứng đúng trang của bước. Chưa thì chỉ phủ tối và để linh vật chạy trong lúc đổi trang. */
  onPage: boolean;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onFinish: (href?: string) => void;
  /** Target không xuất hiện sau 5 giây: provider bỏ qua bước này. */
  onMissing: () => void;
}

export function TourOverlay({ step, name, chapters, first, last, onPage, onNext, onPrev, onSkip, onFinish, onMissing }: TourOverlayProps) {
  const reduce = useReducedMotion() ?? false;
  const rootRef = useRef<HTMLDivElement>(null);
  const measured = useViewport(rootRef);
  const view = measured ?? { w: 1280, h: 800 };
  const sheet = view.w <= SHEET_MAX;
  const compact = view.w <= COMPACT_MAX;
  const titleId = useId();
  const bodyId = useId();
  const maskId = `tour-mask-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const groupRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [traveling, setTraveling] = useState(false);
  const lastPos = useRef<Box | null>(null);
  const flip = useRef(false);

  const targetName = compact && step.compact?.target ? step.compact.target : step.target;
  const body = compact && step.compact?.body ? step.compact.body : step.body;
  const title = step.title.replace('{name}', name);
  const { status, rect } = useTourTarget(targetName, onPage);

  useEffect(() => {
    if (status === 'missing') onMissing();
  }, [status, onMissing]);

  // Khoá cuộn và vô hiệu nền trong lúc tour chạy; trả lại đúng như cũ khi đóng.
  useEffect(() => {
    const root = document.documentElement;
    const app = document.querySelector<HTMLElement>('[data-app-root]');
    const previous = { overflow: root.style.overflow, gutter: root.style.scrollbarGutter };
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    root.style.overflow = 'hidden';
    root.style.scrollbarGutter = 'stable';
    app?.setAttribute('inert', '');
    for (const src of Object.values(MASCOT_SOURCES)) new window.Image().src = src;
    return () => {
      root.style.overflow = previous.overflow;
      root.style.scrollbarGutter = previous.gutter;
      app?.removeAttribute('inert');
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);

  // Đo thẻ nói để biết chỗ đặt vừa khít trong khung nhìn.
  useEffect(() => {
    const el = groupRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.offsetWidth, h: el.offsetHeight });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const header = typeof document === 'undefined' ? 0 : (document.querySelector('header')?.getBoundingClientRect().height ?? 0);
  const padded: TargetRect | null = onPage && rect ? { x: rect.x - PAD, y: rect.y - PAD, w: rect.w + PAD * 2, h: rect.h + PAD * 2 } : null;
  const waiting = !onPage || status === 'waiting';
  const groupWidth = sheet ? view.w - MARGIN * 2 : Math.min(520, view.w - MARGIN * 2);
  const pos = size && measured ? place(padded, size, view, sheet, header) : null;

  // Đổi vị trí xa thì linh vật chạy; tới nơi (hoặc đứng yên) thì đổi sang dáng đứng.
  useEffect(() => {
    if (!pos) return;
    const from = lastPos.current;
    lastPos.current = pos;
    if (!from || reduce) return;
    const dx = pos.x - from.x;
    if (Math.hypot(dx, pos.y - from.y) > RUN_DISTANCE) {
      flip.current = dx < 0;
      setTraveling(true);
    }
  }, [pos?.x, pos?.y, reduce]);

  // Lần đặt đầu tiên không bay từ góc màn hình; các lần sau mới dùng spring.
  const placed = useRef(false);
  useEffect(() => {
    if (pos) placed.current = true;
  });

  const running = (traveling || waiting) && !reduce;
  const mascotSize = sheet ? 72 : 104;
  const groupCenter = pos && size ? pos.x + size.w / 2 : 0;
  const face: MascotLook = !padded || sheet ? 'front' : groupCenter < padded.x + padded.w / 2 ? 'right' : 'left';
  const look: MascotLook = running ? 'run' : step.pose === 'face' ? face : step.pose;
  const showBubble = !waiting && !traveling;

  // Mỗi bước xong di chuyển thì đưa focus vào nút chính để Enter đi tiếp.
  useEffect(() => {
    if (showBubble) groupRef.current?.querySelector<HTMLElement>('[data-tour-primary]')?.focus({ preventScroll: true });
  }, [showBubble, step.id]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        if (last) onFinish();
        else onSkip();
      } else if (event.key === 'ArrowRight' && !last) {
        event.preventDefault();
        onNext();
      } else if (event.key === 'ArrowLeft' && !first) {
        event.preventDefault();
        onPrev();
      } else if (event.key === 'Tab') {
        const focusable = groupRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]');
        if (!focusable?.length) return;
        const [start, end] = [focusable[0], focusable[focusable.length - 1]];
        if (event.shiftKey && document.activeElement === start) {
          event.preventDefault();
          end.focus();
        } else if (!event.shiftKey && document.activeElement === end) {
          event.preventDefault();
          start.focus();
        } else if (!groupRef.current?.contains(document.activeElement)) {
          event.preventDefault();
          start.focus();
        }
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [first, last, onFinish, onNext, onPrev, onSkip]);

  const transition = reduce || !placed.current ? instant : spring;
  // Không có target: ô khoét thu về một điểm giữa màn hình, cả màn hình tối.
  const spot = padded ?? { x: view.w / 2, y: view.h / 2, w: 0, h: 0 };

  return createPortal(
    <motion.div
      ref={rootRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.2 } }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-[80]"
    >
      {/* Lớp tối: SVG có mask khoét một ô bo góc theo phần tử đang chỉ. */}
      <svg aria-hidden="true" className="absolute inset-0 size-full">
        <defs>
          <mask id={maskId}>
            <rect width="100%" height="100%" fill="white" />
            <motion.rect
              rx={16}
              fill="black"
              initial={false}
              animate={{ x: spot.x, y: spot.y, width: spot.w, height: spot.h }}
              transition={transition}
            />
          </mask>
        </defs>
        <rect width="100%" height="100%" mask={`url(#${maskId})`} className="fill-foreground/78" />
      </svg>
      <motion.div
        aria-hidden="true"
        initial={false}
        animate={{ x: spot.x, y: spot.y, width: spot.w, height: spot.h, opacity: padded ? 1 : 0 }}
        transition={transition}
        className="absolute top-0 left-0 rounded-2xl border-2 border-accent"
      />

      <motion.div
        ref={groupRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        initial={false}
        animate={{ x: pos?.x ?? 0, y: pos?.y ?? 0, opacity: pos ? 1 : 0 }}
        transition={transition}
        onAnimationComplete={() => setTraveling(false)}
        style={{ width: groupWidth }}
        className={cn('absolute top-0 left-0 flex', sheet ? 'flex-col items-start' : 'items-end gap-2')}
      >
        <div className={cn(sheet && 'relative z-10 ml-3 -mb-5')}>
          <TourMascot look={look} size={mascotSize} flip={running && flip.current} bob={!running} />
        </div>
        <motion.div
          initial={false}
          animate={{ opacity: showBubble ? 1 : 0, y: showBubble ? 0 : 6 }}
          transition={{ duration: reduce ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
          aria-live="polite"
          inert={!showBubble}
          className={cn('min-w-0', sheet ? 'w-full' : 'flex-1')}
        >
          <TourBubble
            titleId={titleId}
            bodyId={bodyId}
            title={title}
            body={body}
            chapter={step.chapter}
            chapters={chapters}
            first={first}
            last={last}
            sheet={sheet}
            onNext={onNext}
            onPrev={onPrev}
            onSkip={onSkip}
            onFinish={onFinish}
          />
        </motion.div>
      </motion.div>
    </motion.div>,
    document.body,
  );
}
