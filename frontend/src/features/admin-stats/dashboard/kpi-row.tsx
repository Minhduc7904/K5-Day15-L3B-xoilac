'use client';

/** Hàng chỉ số đầu dashboard: giá trị kỳ này kèm mức thay đổi so với kỳ liền trước cùng độ dài. */
import { Minus, TrendingDown, TrendingUp } from 'lucide-react';
import { Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import type { Kpi } from '../analytics-api';
import { fmtInt, fmtPct, fmtScore } from '../charts/chart-theme';

type Format = 'count' | 'score' | 'rate';

const KPI_META: Record<string, { label: string; format: Format; compare: boolean }> = {
  active_students: { label: 'Học sinh hoạt động', format: 'count', compare: true },
  new_students: { label: 'Đăng ký mới', format: 'count', compare: true },
  completed_attempts: { label: 'Bài làm hoàn thành', format: 'count', compare: true },
  average_score: { label: 'Điểm trung bình', format: 'score', compare: true },
  published_questions: { label: 'Câu hỏi đang dùng', format: 'count', compare: false },
  import_success_rate: { label: 'Nhập đề PDF thành công', format: 'rate', compare: true },
};
const ORDER = Object.keys(KPI_META);

const show = (value: number | null, format: Format) =>
  value === null ? '—' : format === 'rate' ? fmtPct(value) : format === 'score' ? fmtScore(value) : fmtInt(value);

/** Trả chữ mô tả thay đổi và chiều (1 tăng, -1 giảm, 0 giữ nguyên). null khi không so sánh được. */
function delta(kpi: Kpi, format: Format): { text: string; dir: 1 | 0 | -1 } | null {
  const { value, previous } = kpi;
  if (value === null || previous === null) return null;
  const diff = value - previous;
  if (Math.abs(diff) < 1e-9) return { text: 'Không đổi', dir: 0 };
  const dir = diff > 0 ? 1 : -1;
  const sign = diff > 0 ? '+' : '−';
  if (format === 'score') return { text: `${sign}${fmtScore(Math.abs(diff))} điểm`, dir };
  if (format === 'rate') return { text: `${sign}${fmtInt(Math.round(Math.abs(diff) * 100))} điểm %`, dir };
  if (previous === 0) return { text: `${sign}${fmtInt(Math.abs(diff))} (kỳ trước là 0)`, dir };
  return { text: `${sign}${fmtInt(Math.round((Math.abs(diff) / previous) * 100))}%`, dir };
}

export function KpiRow({ kpis, days, loading }: { kpis: Kpi[] | undefined; days: number; loading: boolean }) {
  const byKey = new Map((kpis ?? []).map((k) => [k.key, k]));
  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
      {ORDER.map((key) => {
        const meta = KPI_META[key];
        const kpi = byKey.get(key);
        const change = kpi && meta.compare ? delta(kpi, meta.format) : null;
        const Icon = change?.dir === 1 ? TrendingUp : change?.dir === -1 ? TrendingDown : Minus;
        return (
          <div key={key} className="grid min-w-0 gap-1 rounded-2xl border border-border bg-background p-4">
            <dt className="text-caption text-muted-foreground">{meta.label}</dt>
            <dd className="grid gap-1">
              {kpi ? (
                <span className={cn('text-h2 font-semibold text-foreground', loading && 'opacity-60')}>{show(kpi.value, meta.format)}</span>
              ) : (
                <Skeleton className="h-9 w-20" />
              )}
              {meta.compare && (
                <span className={cn('flex items-center gap-1 text-caption', change?.dir === 1 ? 'text-success' : change?.dir === -1 ? 'text-danger' : 'text-muted-foreground')}>
                  {change ? (
                    <>
                      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
                      <span className="font-semibold tabular-nums">{change.text}</span>
                      <span className="text-muted-foreground">so với {days} ngày trước</span>
                    </>
                  ) : kpi ? (
                    <span>Chưa có kỳ trước để so sánh</span>
                  ) : null}
                </span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
