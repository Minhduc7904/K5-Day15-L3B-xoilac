'use client';

import { useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { cn } from '@/lib/cn';

export interface Segment {
  label: string;
  /** Lớp nền của đoạn (vd `bg-primary`). */
  color: string;
}

interface Props {
  label: string;
  max: number;
  step?: number;
  /** Vị trí cộng dồn của các vạch, tăng dần. */
  values: number[];
  segments: Segment[];
  /** Vạch cuối không được nhỏ hơn giá trị này (vd tổng ít nhất 1 câu). */
  minLast?: number;
  disabled?: boolean;
  /** Chữ đọc cho trình đọc màn hình và bong bóng khi kéo, theo chỉ số vạch. */
  valueText: (index: number, values: number[]) => string;
  onChange: (values: number[]) => void;
}

/**
 * Thanh kéo nhiều vạch chia một khoảng thành các đoạn liền nhau.
 * Có `segments.length` đoạn: nếu số vạch bằng số đoạn thì phần sau vạch cuối để trống (vd tổng câu < max),
 * nếu ít hơn một thì đoạn cuối kéo tới hết thanh (vd phần trăm độ khó).
 */
export function SegmentSlider({ label, max, step = 1, values, segments, minLast = 0, disabled, valueText, onChange }: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<number | null>(null);
  const pending = useRef<{ candidates: number[]; x: number } | null>(null);

  const bounds = (i: number, vals: number[]) => {
    const lo = Math.max(i === 0 ? 0 : vals[i - 1], i === vals.length - 1 ? minLast : 0);
    const hi = i === vals.length - 1 ? max : vals[i + 1];
    return [lo, hi] as const;
  };

  const setThumb = (i: number, raw: number) => {
    const [lo, hi] = bounds(i, values);
    const v = Math.min(hi, Math.max(lo, Math.round(raw / step) * step));
    if (v === values[i]) return;
    onChange(values.map((x, k) => (k === i ? v : x)));
  };

  const valueAt = (clientX: number) => {
    const rect = trackRef.current!.getBoundingClientRect();
    return ((clientX - rect.left) / rect.width) * max;
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (disabled) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    const v = valueAt(e.clientX);
    const dist = values.map((x) => Math.abs(x - v));
    const best = Math.min(...dist);
    const candidates = dist.flatMap((d, i) => (d - best < 1e-6 ? [i] : []));
    if (candidates.length === 1) {
      setActive(candidates[0]);
      setThumb(candidates[0], v);
      (trackRef.current?.querySelectorAll<HTMLElement>('[role="slider"]')[candidates[0]])?.focus();
    } else {
      // Nhiều vạch chồng nhau: chờ hướng kéo để chọn vạch.
      pending.current = { candidates, x: e.clientX };
    }
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (pending.current) {
      const dx = e.clientX - pending.current.x;
      if (Math.abs(dx) < 3) return;
      const { candidates } = pending.current;
      const pick = dx > 0 ? candidates[candidates.length - 1] : candidates[0];
      pending.current = null;
      setActive(pick);
      (trackRef.current?.querySelectorAll<HTMLElement>('[role="slider"]')[pick])?.focus();
    }
    if (active !== null) setThumb(active, valueAt(e.clientX));
  };

  const end = () => {
    pending.current = null;
    setActive(null);
  };

  const onKeyDown = (i: number) => (e: KeyboardEvent<HTMLDivElement>) => {
    const [lo, hi] = bounds(i, values);
    const big = step * 5;
    const map: Record<string, number> = {
      ArrowRight: values[i] + step,
      ArrowUp: values[i] + step,
      ArrowLeft: values[i] - step,
      ArrowDown: values[i] - step,
      PageUp: values[i] + big,
      PageDown: values[i] - big,
      Home: lo,
      End: hi,
    };
    if (!(e.key in map)) return;
    e.preventDefault();
    setThumb(i, map[e.key]);
  };

  const pct = (v: number) => `${(v / max) * 100}%`;

  return (
    <div className={cn('relative px-2.5 pt-1 pb-1', disabled && 'opacity-60')}>
      <div
        ref={trackRef}
        role="group"
        aria-label={label}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={end}
        onPointerCancel={end}
        className={cn('relative h-7 touch-none select-none', disabled ? 'cursor-not-allowed' : 'cursor-pointer')}
      >
        <div className="absolute inset-x-0 top-1/2 flex h-3 -translate-y-1/2 overflow-hidden rounded-full bg-surface-muted">
          {segments.map((seg, i) => {
            const from = i === 0 ? 0 : values[i - 1];
            const to = values[i] ?? max;
            return <span key={seg.label} className={cn('h-full transition-[width] duration-75', seg.color)} style={{ width: pct(to - from) }} />;
          })}
        </div>
        {values.map((v, i) => (
          <div
            key={i}
            role="slider"
            tabIndex={disabled ? -1 : 0}
            aria-label={`Vạch ${i + 1}: hết phần ${segments[i].label}`}
            aria-valuemin={bounds(i, values)[0]}
            aria-valuemax={bounds(i, values)[1]}
            aria-valuenow={v}
            aria-valuetext={valueText(i, values)}
            aria-disabled={disabled || undefined}
            onKeyDown={onKeyDown(i)}
            className={cn(
              'group absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-foreground bg-background shadow-soft transition-transform outline-none focus-visible:ring-4 focus-visible:ring-ring/35',
              active === i ? 'scale-125 cursor-grabbing' : 'hover:scale-110',
            )}
            style={{ left: pct(v), zIndex: active === i ? 3 : i === values.length - 1 ? 2 : 1 }}
          >
            <span
              aria-hidden="true"
              className={cn(
                'pointer-events-none absolute bottom-full mb-2 rounded-md bg-foreground px-1.5 py-0.5 text-[0.6875rem] font-semibold whitespace-nowrap text-background tabular-nums transition-opacity',
                active === i ? 'opacity-100' : 'opacity-0 group-focus-visible:opacity-100',
                // Gần mép thì neo bong bóng vào trong để không tràn ra ngoài khung.
                v / max > 0.75 ? 'right-0' : v / max < 0.25 ? 'left-0' : 'left-1/2 -translate-x-1/2',
              )}
            >
              {valueText(i, values)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
