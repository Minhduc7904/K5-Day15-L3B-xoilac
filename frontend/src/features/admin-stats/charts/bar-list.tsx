'use client';

/** Danh sách thanh ngang HTML: so sánh vài chục mục có nhãn dài (chương, trạng thái) và các bước phễu. Giá trị in ở đầu thanh. */
import { cn } from '@/lib/cn';
import { CHART } from './chart-theme';

export interface BarRow {
  key: string;
  label: string;
  value: number;
  /** Chữ hiển thị bên phải; mặc định là `value`. */
  valueLabel?: string;
  /** Dòng phụ nhỏ dưới nhãn. */
  hint?: string;
  /** Ghi đè màu thanh (dùng cho phễu theo thang thứ tự). */
  color?: string;
}

export function BarList({ rows, max, color = CHART.s1, className }: { rows: BarRow[]; max?: number; color?: string; className?: string }) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value));
  return (
    <ul className={cn('grid gap-3', className)}>
      {rows.map((row) => (
        <li key={row.key} className="grid gap-1">
          <div className="flex items-baseline justify-between gap-3 text-caption">
            <span className="min-w-0 truncate text-foreground" title={row.label}>{row.label}</span>
            <span className="shrink-0 font-semibold text-foreground tabular-nums">{row.valueLabel ?? row.value}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-muted" role="presentation">
            <div className="h-full rounded-full" style={{ width: `${Math.max(row.value > 0 ? 2 : 0, (row.value / top) * 100)}%`, backgroundColor: row.color ?? color }} />
          </div>
          {row.hint && <span className="text-caption text-muted-foreground">{row.hint}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Một đại lượng được chia thành các phần (vd trạng thái câu hỏi): thanh phân đoạn cao 28px, khoảng hở 2px. */
export function SegmentedBar({ parts, label }: { parts: Array<{ key: string; label: string; value: number; color: string }>; label: string }) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  if (total === 0) return null;
  return (
    <div role="img" aria-label={`${label}: ${parts.map((p) => `${p.label} ${p.value}`).join(', ')}`} className="flex h-7 gap-0.5">
      {parts.filter((p) => p.value > 0).map((p) => (
        <div key={p.key} title={`${p.label}: ${p.value}`} className="min-w-1 rounded first:rounded-l-md last:rounded-r-md" style={{ flexGrow: p.value, backgroundColor: p.color }} />
      ))}
    </div>
  );
}
