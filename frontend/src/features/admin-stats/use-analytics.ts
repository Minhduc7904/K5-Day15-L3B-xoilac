'use client';

import { useCallback, useEffect, useState } from 'react';
import { toApiError, type ApiError } from '@/lib/api-error';
import type { RangeDays } from './analytics-api';

export interface AnalyticsState<T> {
  data: T | null;
  error: ApiError | null;
  /** Đang tải lần đầu hoặc tải lại khi đổi khoảng thời gian (data cũ vẫn còn để giữ bố cục). */
  loading: boolean;
  reload: () => void;
}

/** Nạp một nhóm thống kê theo khoảng thời gian. Đổi khoảng thì giữ số liệu cũ tới khi có số liệu mới. */
export function useAnalytics<T>(load: (range: RangeDays) => Promise<T>, range: RangeDays): AnalyticsState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    load(range)
      .then((next) => {
        if (cancelled) return;
        setData(next);
        setError(null);
      })
      .catch((e) => !cancelled && setError(toApiError(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // `load` là hàm tĩnh của adminAnalyticsApi nên không cần đưa vào phụ thuộc.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data, error, loading, reload };
}
