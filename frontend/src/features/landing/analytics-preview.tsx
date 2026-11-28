'use client';

import { Flame, TrendingUp } from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Container, Section, SectionHeader } from '@/components/layout/container';
import { Reveal, Stagger, StaggerItem } from '@/components/motion/reveal';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/feedback';

/** Toàn bộ số liệu dưới đây là ví dụ minh hoạ, không phải dữ liệu học sinh thật. */
const scores = [
  { name: 'Đề 1', score: 5.5 },
  { name: 'Đề 2', score: 6 },
  { name: 'Đề 3', score: 5.75 },
  { name: 'Đề 4', score: 6.75 },
  { name: 'Đề 5', score: 7.25 },
  { name: 'Đề 6', score: 7 },
  { name: 'Đề 7', score: 7.75 },
  { name: 'Đề 8', score: 8.5 },
];

const radar = [
  { skill: 'Đạo hàm', value: 82 },
  { skill: 'Tích phân', value: 64 },
  { skill: 'Hình KG', value: 48 },
  { skill: 'Xác suất', value: 76 },
  { skill: 'Mũ–log', value: 70 },
  { skill: 'Lượng giác', value: 58 },
];

const week = [
  { day: 'T2', questions: 14 },
  { day: 'T3', questions: 22 },
  { day: 'T4', questions: 0 },
  { day: 'T5', questions: 18 },
  { day: 'T6', questions: 26 },
  { day: 'T7', questions: 31 },
  { day: 'CN', questions: 12 },
];

const kpis = [
  { label: 'Câu đã làm', value: '126' },
  { label: 'Tỉ lệ đúng', value: '72%' },
  { label: 'TB mỗi câu', value: '72 giây' },
];

const tick = { fill: 'var(--color-muted-foreground)', fontSize: 11 };
const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid var(--color-border)',
  boxShadow: 'var(--shadow-soft)',
  fontSize: 12,
  color: 'var(--color-foreground)',
} as const;

function CardTitle({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <h3 className="text-h3 text-foreground">{title}</h3>
        <p className="mt-0.5 text-caption text-muted-foreground">{hint}</p>
      </div>
      <Badge tone="neutral" className="shrink-0 whitespace-nowrap">
        Ví dụ
      </Badge>
    </div>
  );
}

export function AnalyticsPreview() {
  return (
    <Section id="thong-ke" tone="surface" aria-labelledby="thong-ke-title" className="overflow-hidden">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-50" aria-hidden="true" />
      <Container className="relative">
        <Reveal>
          <SectionHeader
            titleId="thong-ke-title"
            eyebrow="Thống kê học tập"
            title="Nhìn một lần là biết mình đang ở đâu"
            description="Sau mỗi lần làm bài, điểm, hồ sơ năng lực và chuỗi ngày học cập nhật ngay trên trang tổng quan của bạn."
          />
        </Reveal>

        <Stagger className="mt-14 grid gap-5 lg:grid-cols-3" stagger={0.1}>
          <StaggerItem className="lg:col-span-2">
            <Card className="h-full p-6 sm:p-7">
              <CardTitle title="Điểm qua các đề" hint="Điểm luyện tập trên thang 10" />
              <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
                <p className="flex items-baseline gap-2">
                  <strong className="text-display leading-none font-bold tracking-tight text-foreground tabular-nums">8,5</strong>
                  <span className="text-label text-muted-foreground">điểm gần nhất</span>
                </p>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-success-subtle px-3 py-1 text-label font-semibold text-success tabular-nums">
                  <TrendingUp className="size-4" aria-hidden="true" />
                  +0,75 so với lượt trước
                </span>
              </div>
              <div className="mt-4 h-60 w-full" role="img" aria-label="Biểu đồ điểm tăng dần qua tám đề, từ 5,5 lên 8,5">
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <AreaChart data={scores} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
                    <defs>
                      <linearGradient id="landing-score" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 4" />
                    <XAxis dataKey="name" tick={tick} tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 10]} ticks={[0, 2.5, 5, 7.5, 10]} tick={tick} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      cursor={{ stroke: 'var(--color-primary)', strokeOpacity: 0.2 }}
                      formatter={(v) => [`${String(v).replace('.', ',')} điểm`, 'Điểm']}
                    />
                    <Area
                      type="monotone"
                      dataKey="score"
                      stroke="var(--color-primary)"
                      strokeWidth={3}
                      fill="url(#landing-score)"
                      dot={{ r: 4, fill: 'var(--color-background)', stroke: 'var(--color-primary)', strokeWidth: 2 }}
                      activeDot={{ r: 6, fill: 'var(--color-accent)', stroke: 'var(--color-background)', strokeWidth: 2 }}
                      animationDuration={1400}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </StaggerItem>

          <StaggerItem>
            <Card className="h-full p-6 sm:p-7">
              <CardTitle title="Hồ sơ học tập" hint="Tỉ lệ đúng theo mảng kiến thức" />
              <div className="mt-2 h-72 w-full" role="img" aria-label="Biểu đồ radar: mạnh nhất ở đạo hàm 82%, yếu nhất ở hình học không gian 48%">
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <RadarChart data={radar} outerRadius="80%" margin={{ top: 8, right: 44, bottom: 8, left: 52 }}>
                    <PolarGrid stroke="var(--color-border)" />
                    <PolarAngleAxis dataKey="skill" tick={tick} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, 'Tỉ lệ đúng']} />
                    <Radar
                      dataKey="value"
                      stroke="var(--color-accent-strong)"
                      strokeWidth={2.5}
                      fill="var(--color-accent)"
                      fillOpacity={0.3}
                      animationDuration={1400}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-caption text-muted-foreground">
                Điểm yếu nhất: <strong className="text-danger">Hình học không gian (48%)</strong>
              </p>
            </Card>
          </StaggerItem>

          <StaggerItem>
            <Card className="h-full p-6 sm:p-7">
              <CardTitle title="Tổng quan" hint="Sau 8 đề luyện" />
              <ul className="mt-5 grid gap-3">
                {kpis.map((k) => (
                  <li key={k.label} className="flex items-baseline justify-between gap-3 rounded-2xl bg-surface px-4 py-3">
                    <span className="text-label text-muted-foreground">{k.label}</span>
                    <span className="text-h2 font-bold whitespace-nowrap text-foreground tabular-nums">{k.value}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </StaggerItem>

          <StaggerItem className="lg:col-span-2">
            <Card className="h-full p-6 sm:p-7">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-h3 text-foreground">Chuỗi ngày học</h3>
                  <p className="mt-0.5 text-caption text-muted-foreground">Số câu làm mỗi ngày trong 7 ngày gần nhất</p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-flame-subtle px-3 py-1 text-label font-semibold text-flame-strong tabular-nums">
                  <Flame className="size-4 text-flame" aria-hidden="true" />
                  Chuỗi 3 ngày
                </span>
              </div>
              <div className="mt-4 h-48 w-full" role="img" aria-label="Biểu đồ cột số câu làm theo ngày, nhiều nhất thứ Bảy 31 câu">
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <BarChart data={week} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
                    <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 4" />
                    <XAxis dataKey="day" tick={tick} tickLine={false} axisLine={false} />
                    <YAxis tick={tick} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      cursor={{ fill: 'var(--color-primary-subtle)' }}
                      formatter={(v) => [`${v} câu`, 'Đã làm']}
                    />
                    <Bar dataKey="questions" fill="var(--color-primary)" radius={[8, 8, 0, 0]} maxBarSize={36} animationDuration={1200} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </StaggerItem>
        </Stagger>
      </Container>
    </Section>
  );
}
