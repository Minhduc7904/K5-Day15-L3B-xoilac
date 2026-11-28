'use client';

/** Chart đường/vùng và cột (recharts) cho dashboard admin. Quy cách mark theo skill dataviz: đường 2px, cột ≤ 24px bo 4px ở đầu, lưới hairline. */
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  type TooltipContentProps,
} from 'recharts';
import { CHART, fmtInt, tickStyle } from './chart-theme';

export interface Series {
  key: string;
  label: string;
  color: string;
}

interface BaseProps {
  data: Array<Record<string, number | string | null>>;
  xKey: string;
  series: Series[];
  /** Định dạng nhãn trục X và tiêu đề tooltip. */
  xFormat?: (value: string) => string;
  /** Định dạng giá trị trong tooltip. */
  valueFormat?: (value: number) => string;
  height?: number;
  /** Trục Y cố định, ví dụ [0, 10] cho điểm. */
  yDomain?: [number, number];
  yTicks?: number[];
}

const margin = { top: 8, right: 12, bottom: 0, left: 0 };

function Tip({ active, payload, label, xFormat, valueFormat = fmtInt }: Pick<TooltipContentProps<number, string>, 'active' | 'payload' | 'label'> & Pick<BaseProps, 'xFormat' | 'valueFormat'>) {
  if (!active || !payload?.length) return null;
  const title = String(label ?? '');
  return (
    <div className="grid gap-1 rounded-lg bg-foreground px-3 py-2 text-background shadow-soft">
      <p className="text-caption text-background/80">{xFormat ? xFormat(title) : title}</p>
      {payload.map((p) => (
        <p key={String(p.dataKey)} className="flex items-center gap-2 text-caption">
          <span className="size-2 rounded-sm" style={{ backgroundColor: p.color ?? p.stroke }} aria-hidden="true" />
          <span className="text-background/80">{p.name}</span>
          <span className="ml-auto pl-3 font-semibold tabular-nums">{p.value == null ? '—' : valueFormat(Number(p.value))}</span>
        </p>
      ))}
    </div>
  );
}

function axes({ xKey, xFormat, yDomain, yTicks }: Pick<BaseProps, 'xKey' | 'xFormat' | 'yDomain' | 'yTicks'>) {
  return (
    <>
      <CartesianGrid vertical={false} stroke={CHART.grid} />
      <XAxis dataKey={xKey} tickLine={false} axisLine={{ stroke: CHART.grid }} tick={tickStyle} tickMargin={8} minTickGap={16} tickFormatter={xFormat} />
      <YAxis width={32} tickLine={false} axisLine={false} tick={tickStyle} allowDecimals={false} domain={yDomain} ticks={yTicks} />
    </>
  );
}

/** Một chuỗi: đường kèm vùng tô nhạt (~10%). Từ hai chuỗi: các đường, không tô vùng. */
export function TrendChart({ data, xKey, series, xFormat, valueFormat, height = 220, yDomain, yTicks }: BaseProps) {
  const cursor = { stroke: CHART.axis, strokeDasharray: '3 4' };
  const tooltip = <Tooltip isAnimationActive={false} cursor={cursor} content={(p) => <Tip {...p} xFormat={xFormat} valueFormat={valueFormat} />} />;
  const dot = { r: 4, stroke: CHART.surface, strokeWidth: 2 };
  return (
    <div style={{ height }} className="min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        {series.length === 1 ? (
          <AreaChart data={data} margin={margin} accessibilityLayer>
            {axes({ xKey, xFormat, yDomain, yTicks })}
            {tooltip}
            <Area type="monotone" dataKey={series[0].key} name={series[0].label} stroke={series[0].color} strokeWidth={2} fill={series[0].color} fillOpacity={0.1} dot={false} activeDot={{ ...dot, fill: series[0].color }} isAnimationActive={false} />
          </AreaChart>
        ) : (
          <LineChart data={data} margin={margin} accessibilityLayer>
            {axes({ xKey, xFormat, yDomain, yTicks })}
            {tooltip}
            {series.map((s) => (
              <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" dot={false} activeDot={{ ...dot, fill: s.color }} connectNulls isAnimationActive={false} />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

/** Cột đơn, cột nhóm hoặc cột chồng (có khoảng hở 2px giữa các đoạn). */
export function ColumnsChart({ data, xKey, series, xFormat, valueFormat, height = 220, stacked = false, yDomain, yTicks }: BaseProps & { stacked?: boolean }) {
  return (
    <div style={{ height }} className="min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={data} margin={margin} barCategoryGap="25%" accessibilityLayer>
          {axes({ xKey, xFormat, yDomain, yTicks })}
          <Tooltip isAnimationActive={false} cursor={{ fill: CHART.grid, fillOpacity: 0.5 }} content={(p) => <Tip {...p} xFormat={xFormat} valueFormat={valueFormat} />} />
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={s.color}
              maxBarSize={24}
              stackId={stacked ? 'stack' : undefined}
              stroke={stacked ? CHART.surface : undefined}
              strokeWidth={stacked ? 2 : 0}
              radius={stacked ? (i === series.length - 1 ? [4, 4, 0, 0] : 0) : [4, 4, 0, 0]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
