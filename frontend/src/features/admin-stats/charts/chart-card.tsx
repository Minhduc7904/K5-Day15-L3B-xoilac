'use client';

/**
 * Khung một chart: tiêu đề là câu kết luận, mô tả phạm vi, chú giải, nút chuyển Biểu đồ/Bảng và đủ trạng thái
 * đang tải / lỗi / trống. Bảng số liệu là kênh thay thế cho người không phân biệt được màu hoặc dùng trình đọc màn hình.
 */
import { RefreshCw } from 'lucide-react';
import { useId, useState, type ReactNode } from 'react';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import type { ApiError } from '@/lib/api-error';

export interface LegendItem {
  label: string;
  color: string;
}

export interface DataTable {
  columns: string[];
  rows: Array<Array<string | number>>;
}

interface ChartCardProps {
  title: string;
  description?: string;
  legend?: LegendItem[];
  table?: DataTable;
  loading?: boolean;
  error?: ApiError | null;
  onRetry?: () => void;
  /** Có dữ liệu để vẽ không. false hiện `emptyText` thay cho chart. */
  hasData?: boolean;
  emptyText?: string;
  className?: string;
  children: ReactNode;
}

export function ChartCard({
  title, description, legend, table, loading, error, onRetry, hasData = true, emptyText = 'Chưa có dữ liệu trong khoảng này.',
  className, children,
}: ChartCardProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart');
  const titleId = useId();
  const showTable = view === 'table' && table;
  const firstLoad = loading && !hasData;

  return (
    <section aria-labelledby={titleId} className={cn('flex min-w-0 flex-col gap-3 rounded-2xl border border-border bg-background p-5', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="grid gap-1">
          <h3 id={titleId} className="text-label font-semibold text-balance text-foreground">{title}</h3>
          {description && <p className="text-caption text-muted-foreground">{description}</p>}
        </div>
        {table && hasData && !error && (
          <div role="group" aria-label="Cách xem" className="flex shrink-0 rounded-lg bg-surface p-0.5 text-caption">
            {(['chart', 'table'] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                onClick={() => setView(v)}
                className={cn(
                  'rounded-md px-2.5 py-1 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                  view === v ? 'bg-background text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {v === 'chart' ? 'Biểu đồ' : 'Bảng'}
              </button>
            ))}
          </div>
        )}
      </div>

      {legend && legend.length > 1 && !showTable && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-caption text-muted-foreground">
          {legend.map((item) => (
            <li key={item.label} className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm" style={{ backgroundColor: item.color }} aria-hidden="true" />
              {item.label}
            </li>
          ))}
        </ul>
      )}

      <div className={cn('min-w-0 flex-1 transition-opacity', loading && hasData && 'opacity-60')} aria-busy={loading || undefined}>
        {error && !hasData ? (
          <Alert
            tone="danger"
            title="Không tải được số liệu"
            action={onRetry && (
              <button type="button" onClick={onRetry} className="inline-flex items-center gap-1.5 text-label font-semibold text-danger underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring">
                <RefreshCw className="size-4" aria-hidden="true" /> Thử lại
              </button>
            )}
          >
            {error.message}
          </Alert>
        ) : firstLoad ? (
          <Skeleton className="h-48 w-full" />
        ) : !hasData ? (
          <p className="grid h-32 place-items-center rounded-xl border border-dashed border-border px-4 text-center text-label text-muted-foreground">
            {emptyText}
          </p>
        ) : showTable ? (
          <DataTableView table={table} />
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function DataTableView({ table }: { table: DataTable }) {
  return (
    <div className="max-h-72 overflow-auto rounded-xl border border-border">
      <table className="w-full text-left text-caption">
        <thead className="sticky top-0 bg-surface text-muted-foreground">
          <tr>
            {table.columns.map((c) => (
              <th key={c} scope="col" className="px-3 py-2 font-semibold whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i} className="border-t border-border">
              {row.map((cell, j) => (
                <td key={j} className={cn('px-3 py-1.5 whitespace-nowrap', j > 0 && 'tabular-nums')}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
