'use client';

import Image from 'next/image';
import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState, type ReactNode } from 'react';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { bootstrapSteps, wait, withTimeout } from '@/lib/bootstrap';
import { useAppDispatch } from '@/store';

/** Lần đầu trong phiên trình duyệt hiện lâu hơn để linh vật chạy trọn vài vòng; tải lại thì ngắn. */
const MIN_FIRST_MS = 1600;
const MIN_REPEAT_MS = 500;
const SEEN_KEY = 'examind:splash-seen';

function readSeen() {
  try {
    return window.sessionStorage.getItem(SEEN_KEY) === '1';
  } catch {
    return false;
  }
}

function markSeen() {
  try {
    window.sessionStorage.setItem(SEEN_KEY, '1');
  } catch {
    /* trình duyệt chặn storage: bỏ qua */
  }
}

export function SplashScreen({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const dispatch = useAppDispatch();

  useEffect(() => {
    let cancelled = false;
    const minDuration = wait(readSeen() ? MIN_REPEAT_MS : MIN_FIRST_MS);

    (async () => {
      for (let i = 0; i < bootstrapSteps.length; i++) {
        if (cancelled) return;
        setStepIndex(i);
        await withTimeout(bootstrapSteps[i].run({ dispatch }).catch(() => undefined));
      }
      if (cancelled) return;
      setStepIndex(bootstrapSteps.length);
      // Giữ thêm một nhịp để thanh tiến độ kịp chạy đầy trước khi splash mờ đi.
      await Promise.all([minDuration, wait(450)]);
      if (cancelled) return;
      markSeen();
      setReady(true);
    })();

    return () => {
      cancelled = true;
    };
  }, [dispatch]);

  useEffect(() => {
    document.documentElement.style.overflow = ready ? '' : 'hidden';
    // Nội dung bị `inert` khi splash hiện nên autoFocus lúc mount không có tác dụng.
    // Khi splash tắt, trả focus cho phần tử trang đánh dấu `data-autofocus`.
    if (ready) document.querySelector<HTMLElement>('[data-autofocus]')?.focus();
  }, [ready]);

  const progress = Math.round((stepIndex / bootstrapSteps.length) * 100);
  const label = bootstrapSteps[stepIndex] ? `${bootstrapSteps[stepIndex].label}…` : 'Sẵn sàng!';

  return (
    <>
      <div inert={!ready} className="contents">
        {children}
      </div>
      <AnimatePresence>
        {!ready && (
          <motion.div
            key="splash"
            data-splash
            role="status"
            aria-live="polite"
            aria-label="Đang khởi động Examind"
            exit={{ opacity: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } }}
            className="fixed inset-0 z-[100] grid place-items-center overflow-hidden bg-background"
          >
            <div className="bg-grid mask-fade pointer-events-none absolute inset-0" aria-hidden="true" />
            <div
              className="pointer-events-none absolute top-1/2 left-1/2 size-[520px] -translate-1/2 rounded-full bg-accent/10 blur-3xl"
              aria-hidden="true"
            />

            <motion.div
              exit={{ scale: 0.94, y: -12 }}
              transition={{ duration: 0.45 }}
              className="relative grid w-full max-w-xs justify-items-center gap-6 px-6 text-center"
            >
              <div className="relative">
                <motion.div
                  aria-hidden="true"
                  className="absolute inset-x-6 bottom-2 h-4 rounded-full bg-foreground/10 blur-md"
                  animate={{ scaleX: [1, 0.8, 1] }}
                  transition={{ duration: 0.42, repeat: Infinity }}
                />
                <MascotAnimation motion="running" size={168} />
              </div>

              <Image src="/brand/examind-logo.webp" alt="Examind" width={972} height={285} className="h-auto w-40" preload />

              <div className="grid w-full gap-3">
                <div className="h-2 overflow-hidden rounded-full bg-surface-muted">
                  <motion.div
                    className="h-full rounded-full bg-linear-to-r from-primary to-accent"
                    initial={{ width: '6%' }}
                    animate={{ width: `${Math.max(progress, 6)}%` }}
                    transition={{ type: 'spring', stiffness: 180, damping: 26 }}
                  />
                </div>
                <div className="relative h-5 overflow-hidden">
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.p
                      key={label}
                      initial={{ y: 12, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: -12, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="text-caption font-medium text-muted-foreground"
                    >
                      {label}
                    </motion.p>
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
