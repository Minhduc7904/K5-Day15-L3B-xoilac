'use client';

/** Ô "Học sinh online" cho admin (#20): gọi API thống kê, tự làm mới mỗi 15 giây. */
import { RefreshCw, Users } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { IconButton } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { ApiError, toApiError } from '@/lib/api-error';
import { adminStatsApi, type OnlineStats } from './api';

const REFRESH_MS = 15_000;


export function OnlineStudentsCard() {
  const [stats, setStats] = useState<OnlineStats | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [showList, setShowList] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setStats(await adminStatsApi.onlineStudents(showList, 1, 10));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    } finally {
      setLoading(false);
    }
  }, [showList]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh();
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="grid gap-1">
          <CardTitle className="flex items-center gap-2">
            <Users aria-hidden="true" className="size-5 text-primary" /> Học sinh online
          </CardTitle>
          <p className="text-caption text-muted-foreground">
            Tự làm mới mỗi 15 giây
            {stats && ` · cập nhật ${new Date(stats.as_of).toLocaleTimeString('vi-VN')}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <IconButton label="Làm mới" onClick={() => void refresh()} disabled={loading}>
            <RefreshCw aria-hidden="true" className={loading ? 'animate-spin' : undefined} />
          </IconButton>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        {error && <Alert tone="danger" title="Không tải được thống kê">{error.message}</Alert>}
        {!stats && !error ? (
          <Skeleton className="h-16 w-full" />
        ) : stats ? (
          <div className="flex items-end gap-6" aria-live="polite">
            <div>
              <p className="text-h2 font-bold text-foreground">{stats.online_students}</p>
              <p className="text-caption text-muted-foreground">học sinh</p>
            </div>
            <div>
              <p className="text-h3 font-semibold text-foreground">{stats.connections}</p>
              <p className="text-caption text-muted-foreground">kết nối (nhiều tab tính riêng)</p>
            </div>
          </div>
        ) : null}
        <button
          type="button"
          className="w-fit text-label text-primary underline-offset-4 hover:underline"
          onClick={() => setShowList((v) => !v)}
          aria-expanded={showList}
        >
          {showList ? 'Ẩn danh sách' : 'Xem danh sách'}
        </button>
        {showList && stats?.users && (
          <ul className="grid gap-1 text-label">
            {stats.users.length === 0 && <li className="text-muted-foreground">Chưa có học sinh nào online.</li>}
            {stats.users.map((u) => (
              <li key={u.user_id} className="flex justify-between gap-3 rounded-lg bg-surface px-3 py-1.5">
                <span className="truncate">{u.display_name ?? u.email}</span>
                <span className="text-muted-foreground">{u.connections} kết nối</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
