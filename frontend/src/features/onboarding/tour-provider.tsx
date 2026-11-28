'use client';

import { AnimatePresence } from 'motion/react';
import { usePathname, useRouter } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useToast } from '@/components/ui/toast';
import { studyApi } from '@/features/study/api';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppSelector } from '@/store';
import { DEMO_RESULT_ID } from './demo-result';
import { readOnboarding, writeOnboarding, type OnboardingResult } from './storage';
import { TOUR_CHAPTERS, TOUR_STEPS } from './steps';
import { TourOverlay } from './tour-overlay';

interface TourContextValue {
  /** Chạy tour từ bước đầu (về /dashboard nếu đang ở trang khác). Bỏ qua nếu tour đang chạy. */
  start: () => void;
  running: boolean;
}

const TourContext = createContext<TourContextValue | null>(null);

export function useTour() {
  const value = useContext(TourContext);
  if (!value) throw new Error('useTour cần được gọi bên trong TourProvider');
  return value;
}

/** Chờ splash tắt và dashboard tải xong (có ô tạo nhanh) rồi mới tự bật, để khung khoét có chỗ đo. */
const AUTO_START_DELAY_MS = 500;
const AUTO_START_POLL_MS = 400;
const AUTO_START_GIVE_UP_MS = 15_000;

export function TourProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  const hydrated = useHydrated();
  const user = useAppSelector((state) => state.auth.user);
  const userId = user?.user_id ?? null;
  const name = user?.display_name?.trim() || 'bạn';

  const [running, setRunning] = useState(false);
  const [index, setIndex] = useState(0);
  const [resultPath, setResultPath] = useState<string | null>(null);
  const runningRef = useRef(false);
  const direction = useRef<1 | -1>(1);
  const autoTried = useRef<number | null>(null);

  // Không tra được dashboard thì bỏ chặng Kết quả; dashboard rỗng thì chặng này mở kết quả minh hoạ.
  const steps = useMemo(() => TOUR_STEPS.filter((s) => s.chapter !== 'result' || resultPath), [resultPath]);
  const chapters = useMemo(() => TOUR_CHAPTERS.filter((c) => steps.some((s) => s.chapter === c.id)), [steps]);
  const step = steps[Math.min(index, steps.length - 1)];
  const wanted = step?.path === 'result' ? resultPath : step?.path;
  const onPage = !wanted || wanted === pathname;

  const start = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    let path: string | null = null;
    try {
      const latest = (await studyApi.getDashboard()).recent[0]?.attempt.id;
      // Chưa có lượt thật thì dùng kết quả minh hoạ (có biểu ngữ, không ghi vào dữ liệu của học sinh).
      path = `/results/${latest ?? DEMO_RESULT_ID}`;
    } catch {
      /* không tra được lượt làm: tour vẫn chạy, chỉ thiếu chặng Kết quả */
    }
    direction.current = 1;
    setResultPath(path);
    setIndex(0);
    setRunning(true);
  }, []);

  const end = useCallback(
    (result: OnboardingResult, next?: string) => {
      if (userId !== null) writeOnboarding(userId, result);
      runningRef.current = false;
      setRunning(false);
      if (next && next !== pathname) router.push(next);
    },
    [userId, pathname, router],
  );

  const skip = useCallback(() => {
    end('skipped');
    toast({ title: 'Đã bỏ qua hướng dẫn', description: 'Bạn có thể xem lại trong menu tài khoản, mục “Xem lại hướng dẫn”.' });
  }, [end, toast]);

  const finish = useCallback((href?: string) => end('completed', href), [end]);

  const next = useCallback(() => {
    direction.current = 1;
    setIndex((i) => Math.min(i + 1, steps.length - 1));
  }, [steps.length]);

  const prev = useCallback(() => {
    direction.current = -1;
    setIndex((i) => Math.max(i - 1, 0));
  }, []);

  // Target không xuất hiện: bỏ qua bước theo chiều đang đi (đầu tour thì đi tới).
  const missing = useCallback(() => {
    setIndex((i) => {
      const n = i + direction.current;
      return n < 0 || n >= steps.length ? i + 1 : n;
    });
  }, [steps.length]);

  // Sang trang của bước hiện tại. Bước không có `path` thì ở nguyên trang.
  useEffect(() => {
    if (running && wanted && wanted !== pathname) router.push(wanted);
  }, [running, wanted, pathname, router]);

  // Tự bật lần đầu vào /dashboard của mỗi tài khoản.
  useEffect(() => {
    if (!hydrated || userId === null || running || pathname !== '/dashboard' || autoTried.current === userId) return;
    if (readOnboarding(userId)) {
      autoTried.current = userId;
      return;
    }
    let cancelled = false;
    let timer = 0;
    const startedAt = Date.now();
    const poll = () => {
      if (cancelled) return;
      const ready =
        !document.querySelector('[data-splash]') &&
        !document.querySelector('dialog[open]') &&
        document.querySelector('[data-tour="quick-create"]');
      if (ready) {
        autoTried.current = userId;
        timer = window.setTimeout(() => !cancelled && void start(), AUTO_START_DELAY_MS);
      } else if (Date.now() - startedAt < AUTO_START_GIVE_UP_MS) {
        timer = window.setTimeout(poll, AUTO_START_POLL_MS);
      }
    };
    poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [hydrated, userId, running, pathname, start]);

  const value = useMemo<TourContextValue>(() => ({ start: () => void start(), running }), [start, running]);

  return (
    <TourContext.Provider value={value}>
      {children}
      <AnimatePresence>
        {running && step && (
          <TourOverlay
            key="tour"
            step={step}
            name={name}
            chapters={chapters}
            first={index === 0}
            last={index >= steps.length - 1}
            onPage={onPage}
            onNext={next}
            onPrev={prev}
            onSkip={skip}
            onFinish={finish}
            onMissing={missing}
          />
        )}
      </AnimatePresence>
    </TourContext.Provider>
  );
}
