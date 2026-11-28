'use client';

import { useEffect, useState } from 'react';

export interface TargetRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** `none`: bước không có target. `waiting`: đang chờ phần tử xuất hiện. `missing`: quá hạn mà không thấy. */
export type TargetStatus = 'none' | 'waiting' | 'ready' | 'missing';

const WAIT_MS = 5000;
const FIND_EVERY_MS = 100;
const REMEASURE_EVERY_MS = 300;
const EDGE = 16;

/** Phần tử đầu tiên đang hiển thị: link điều hướng có hai bản (thanh desktop và ngăn kéo), một bản bị ẩn. */
function findVisible(name: string) {
  for (const el of document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`)) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) return el;
  }
  return null;
}

/** Cuộn để target nằm gọn trong khung nhìn, dưới header dính. Nhảy ngay (không smooth) vì lúc này nền đang tối. */
function reveal(el: HTMLElement) {
  const header = document.querySelector('header')?.getBoundingClientRect().height ?? 0;
  const r = el.getBoundingClientRect();
  const vh = window.innerHeight;
  if (r.top >= header + EDGE && r.bottom <= vh - EDGE) return;
  const tall = r.height > vh * 0.6;
  el.scrollIntoView({ block: tall ? 'start' : 'center', inline: 'nearest', behavior: 'instant' });
  if (tall) window.scrollBy({ top: -(header + EDGE), behavior: 'instant' });
}

const same = (a: TargetRect | null, b: TargetRect) =>
  a !== null && Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5 && Math.abs(a.w - b.w) < 0.5 && Math.abs(a.h - b.h) < 0.5;

/**
 * Tìm phần tử `[data-tour="name"]`, chờ nó xuất hiện (skeleton, đổi trang), cuộn vào khung nhìn rồi
 * theo dõi vị trí khi cuộn, đổi cỡ cửa sổ hay bố cục dịch chuyển. Giữ rect cũ trong lúc chờ để
 * khung khoét không nhấp nháy giữa hai bước cùng trang.
 */
export function useTourTarget(name: string | undefined, active: boolean) {
  const [state, setState] = useState<{ status: TargetStatus; rect: TargetRect | null }>({ status: 'none', rect: null });

  useEffect(() => {
    if (!active) {
      // Đang đổi trang: bỏ rect của trang cũ để khung khoét không trôi tới chỗ không còn tồn tại.
      setState({ status: 'none', rect: null });
      return;
    }
    if (!name) {
      setState({ status: 'none', rect: null });
      return;
    }

    setState((prev) => ({ ...prev, status: 'waiting' }));
    let el: HTMLElement | null = null;
    let frame = 0;
    let timer = 0;
    let observer: ResizeObserver | undefined;
    const startedAt = Date.now();

    const measure = () => {
      if (!el) return;
      if (!el.isConnected) {
        el = null;
        observer?.disconnect();
        setState((prev) => ({ ...prev, status: 'waiting' }));
        schedule();
        return;
      }
      const r = el.getBoundingClientRect();
      const rect = { x: r.left, y: r.top, w: r.width, h: r.height };
      setState((prev) => (prev.status === 'ready' && same(prev.rect, rect) ? prev : { status: 'ready', rect }));
    };
    const queue = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    const schedule = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(tick, el ? REMEASURE_EVERY_MS : FIND_EVERY_MS);
    };
    const tick = () => {
      if (!el) {
        const found = findVisible(name);
        if (found) {
          el = found;
          reveal(found);
          observer = new ResizeObserver(queue);
          observer.observe(found);
        } else if (Date.now() - startedAt > WAIT_MS) {
          setState((prev) => ({ ...prev, status: 'missing' }));
          return;
        }
      }
      measure();
      schedule();
    };

    tick();
    window.addEventListener('scroll', queue, true);
    window.addEventListener('resize', queue);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener('scroll', queue, true);
      window.removeEventListener('resize', queue);
    };
  }, [name, active]);

  return state;
}
