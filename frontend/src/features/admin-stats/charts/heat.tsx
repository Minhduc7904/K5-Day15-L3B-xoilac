'use client';

/** Hai heatmap HTML: giờ × thứ (khi học sinh bắt đầu làm bài) và chương × độ khó (độ phủ ngân hàng). Thang tuần tự một tông xanh. */
import { cn } from '@/lib/cn';
import { SEQUENTIAL, WEEKDAYS, fmtInt, onSequential, sequentialStep } from './chart-theme';

const HOURS = Array.from({ length: 24 }, (_, h) => h);

export function HourHeatmap({ grid }: { grid: number[][] }) {
  const max = Math.max(0, ...grid.flat());
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[34rem] gap-0.5" style={{ gridTemplateColumns: '4.5rem repeat(24, minmax(0, 1fr))' }} role="img" aria-label="Số bài làm theo thứ trong tuần và giờ trong ngày">
        <span />
        {HOURS.map((h) => (
          <span key={h} className="text-center text-[10px] text-muted-foreground tabular-nums">{h % 3 === 0 ? h : ''}</span>
        ))}
        {grid.map((row, d) => (
          <div key={d} className="contents">
            <span className="pr-2 text-right text-caption leading-5 text-muted-foreground">{WEEKDAYS[d]}</span>
            {row.map((value, h) => {
              const step = sequentialStep(value, max);
              return (
                <span
                  key={h}
                  title={`${WEEKDAYS[d]}, ${h}–${h + 1}h: ${fmtInt(value)} bài`}
                  className="h-5 rounded-sm"
                  style={{ backgroundColor: step < 0 ? 'var(--color-surface-muted)' : SEQUENTIAL[step] }}
                />
              );
            })}
          </div>
        ))}
      </div>
      <p className="mt-2 flex items-center gap-2 text-caption text-muted-foreground">
        Ít
        {SEQUENTIAL.map((c) => <span key={c} className="size-3 rounded-sm" style={{ backgroundColor: c }} aria-hidden="true" />)}
        Nhiều
      </p>
    </div>
  );
}

const DIFFICULTY_LABELS: Record<string, string> = { NB: 'Nhận biết', TH: 'Thông hiểu', VD: 'Vận dụng', VDC: 'Vận dụng cao' };

export function CoverageMatrix({ rows }: { rows: Array<{ code: string; name: string; counts: Record<string, number>; total: number }> }) {
  const difficulties = Object.keys(DIFFICULTY_LABELS);
  const max = Math.max(0, ...rows.flatMap((r) => difficulties.map((d) => r.counts[d] ?? 0)));
  return (
    <div className="max-h-80 overflow-auto rounded-xl border border-border">
      <table className="w-full text-caption">
        <thead className="sticky top-0 bg-surface text-muted-foreground">
          <tr>
            <th scope="col" className="px-3 py-2 text-left font-semibold">Chương</th>
            {difficulties.map((d) => (
              <th key={d} scope="col" className="px-2 py-2 text-center font-semibold" title={DIFFICULTY_LABELS[d]}>{d}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.code} className="border-t border-border">
              <th scope="row" className="max-w-48 truncate px-3 py-1.5 text-left font-medium text-foreground" title={`${row.code} · ${row.name}`}>
                <span className="text-muted-foreground">{row.code}</span> {row.name}
              </th>
              {difficulties.map((d) => {
                const value = row.counts[d] ?? 0;
                const step = sequentialStep(value, max);
                return (
                  <td
                    key={d}
                    title={`${row.code} · ${DIFFICULTY_LABELS[d]}: ${value} câu`}
                    className={cn('h-9 min-w-12 text-center font-semibold tabular-nums', step < 0 && 'bg-warning-subtle text-warning')}
                    style={step < 0 ? undefined : { backgroundColor: SEQUENTIAL[step], color: onSequential(step) }}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
