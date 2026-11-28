'use client';

/**
 * Trang /admin: dashboard phân tích cho admin. Một bộ chọn khoảng thời gian áp cho mọi chart;
 * dải "Cần chú ý" dẫn thẳng tới việc tồn đọng; sau đó là hàng chỉ số và bốn khối chart.
 * Số liệu từ /admin/stats/{overview,growth,learning,bank,operations} (xem docs/api/admin-stats-api.md).
 */
import { CircleAlert } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { cn } from '@/lib/cn';
import { adminAnalyticsApi, RANGES, type RangeDays } from '@/features/admin-stats/analytics-api';
import { BankSection, GrowthSection, LearningSection, OperationsSection } from '@/features/admin-stats/dashboard/sections';
import { KpiRow } from '@/features/admin-stats/dashboard/kpi-row';
import { useAnalytics } from '@/features/admin-stats/use-analytics';
import { PageHeader } from './admin-ui';

function RangePicker({ value, onChange }: { value: RangeDays; onChange: (next: RangeDays) => void }) {
  return (
    <div role="group" aria-label="Khoảng thời gian" className="flex rounded-xl bg-surface p-1 text-label">
      {RANGES.map((days) => (
        <button
          key={days}
          type="button"
          aria-pressed={value === days}
          onClick={() => onChange(days)}
          className={cn(
            'h-9 rounded-lg px-3.5 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring',
            value === days ? 'bg-background text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {days} ngày
        </button>
      ))}
    </div>
  );
}

export function AdminDashboard() {
  const [range, setRange] = useState<RangeDays>(30);
  const { data, error, loading } = useAnalytics(adminAnalyticsApi.overview, range);

  const attention = data?.attention;
  const items = attention
    ? [
        { n: attention.pending_pdf_drafts, text: 'câu từ PDF đang chờ duyệt', href: '/admin/pdf-imports' },
        { n: attention.draft_questions, text: 'câu nháp chưa đăng', href: '/admin/questions?status=DRAFT' },
        { n: attention.failed_imports, text: `lượt nhập PDF lỗi trong ${range} ngày`, href: '/admin/pdf-imports' },
      ].filter((i) => i.n > 0)
    : [];

  return (
    <div className="grid gap-8">
      <PageHeader
        title="Tổng quan"
        description={data ? `Số liệu ${range} ngày gần nhất, cập nhật ${new Date(data.generated_at).toLocaleTimeString('vi-VN')}.` : 'Tình hình học sinh, bài làm và ngân hàng câu hỏi.'}
        actions={<RangePicker value={range} onChange={setRange} />}
      />

      {error && !data && (
        <p role="alert" className="rounded-2xl border border-danger/20 bg-danger-subtle p-4 text-label text-danger">
          Không tải được chỉ số tổng quan: {error.message}
        </p>
      )}

      {items.length > 0 && (
        <section aria-label="Cần chú ý" className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-2xl border border-warning/25 bg-warning-subtle px-4 py-3">
          <CircleAlert className="size-5 shrink-0 text-warning" aria-hidden="true" />
          <ul className="flex flex-wrap gap-x-6 gap-y-1">
            {items.map((item) => (
              <li key={item.text}>
                <Link href={item.href} className="text-label text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                  <strong className="tabular-nums">{item.n}</strong> {item.text}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <KpiRow kpis={data?.kpis} days={range} loading={loading} />
      <GrowthSection range={range} />
      <LearningSection range={range} />
      <BankSection range={range} />
      <OperationsSection range={range} />
    </div>
  );
}
