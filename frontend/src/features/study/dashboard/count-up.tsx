'use client';

import { animate, useInView, useReducedMotion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';

/**
 * Số đếm từ 0 lên `value` khi lọt vào màn hình. Người dùng bật giảm chuyển động thì hiện ngay số cuối.
 * `format` nhận số trung gian (đã làm tròn theo `decimals`) và trả chuỗi hiển thị.
 */
export function CountUp({
  value,
  format = (n) => new Intl.NumberFormat('vi-VN').format(n),
  decimals = 0,
  delay = 0,
}: {
  value: number;
  format?: (n: number) => string;
  decimals?: number;
  delay?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);
  const factor = 10 ** decimals;

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setShown(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 1.1,
      delay,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => setShown(Math.round(latest * factor) / factor),
    });
    return () => controls.stop();
  }, [inView, reduce, value, delay, factor]);

  return (
    <span ref={ref} className="tabular-nums">
      <span aria-hidden="true">{format(shown)}</span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
