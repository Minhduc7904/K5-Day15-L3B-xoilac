'use client';

/** Chỉ báo "học sinh online" ở chân thanh bên: gọi lại API thống kê hiện có, làm mới mỗi 30 giây khi tab đang mở. */
import { useEffect, useState } from 'react';
import { cn } from '@/lib/cn';
import { adminStatsApi } from '@/features/admin-stats/api';

const REFRESH_MS = 30_000;

export function SidebarOnline({ collapsed = false }: { collapsed?: boolean }) {
  const [count, setCount] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      adminStatsApi
        .onlineStudents()
        .then((s) => {
          if (cancelled) return;
          setCount(s.online_students);
          setFailed(false);
        })
        .catch(() => !cancelled && setFailed(true));
    };
    load();
    const timer = window.setInterval(() => document.visibilityState === 'visible' && load(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const text = count === null ? (failed ? 'Chưa có số liệu' : 'Đang tải') : `${count} học sinh online`;
  const live = count !== null && !failed;

  return (
    <p
      className={cn(
        'flex items-center gap-2.5 rounded-xl bg-surface px-3 py-2.5 text-label text-foreground',
        collapsed && 'justify-center px-0',
      )}
      title={text}
      aria-live="polite"
    >
      <span
        className={cn('size-2.5 shrink-0 rounded-full', live ? 'bg-success' : 'bg-input')}
        aria-hidden="true"
      />
      {collapsed ? (
        <>
          <span className="sr-only">{text}</span>
          <span className="tabular-nums" aria-hidden="true">
            {count ?? '–'}
          </span>
        </>
      ) : (
        <span className="min-w-0 truncate tabular-nums">{text}</span>
      )}
    </p>
  );
}
