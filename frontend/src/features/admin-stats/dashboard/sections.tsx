'use client';

/**
 * Bốn khối chart của dashboard admin, mỗi khối trả lời một nhóm câu hỏi và nạp số liệu độc lập:
 * tăng trưởng và giữ chân, học tập và điểm số, ngân hàng câu hỏi, vận hành.
 * Tiêu đề mỗi chart là câu kết luận rút từ chính số liệu.
 */
import type { ReactNode } from 'react';
import { OnlineStudentsCard } from '../online-students-card';
import { adminAnalyticsApi, type RangeDays } from '../analytics-api';
import { useAnalytics } from '../use-analytics';
import { BarList, SegmentedBar, type BarRow } from '../charts/bar-list';
import { CHART, ORDINAL, WEEKDAYS, fmtInt, fmtPct, fmtScore, shortDay } from '../charts/chart-theme';
import { ChartCard } from '../charts/chart-card';
import { ColumnsChart, TrendChart } from '../charts/charts';
import { CoverageMatrix, HourHeatmap } from '../charts/heat';

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const weekLabel = (iso: string) => `Tuần ${shortDay(iso)}`;

function Section({ id, title, description, children }: { id: string; title: string; description: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="grid gap-4">
      <div className="grid gap-0.5">
        <h2 id={id} className="text-h3 font-semibold text-foreground">{title}</h2>
        <p className="text-caption text-muted-foreground">{description}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">{children}</div>
    </section>
  );
}

// ---- A. Tăng trưởng và giữ chân ---------------------------------------------------------------------------

export function GrowthSection({ range }: { range: RangeDays }) {
  const { data, error, loading, reload } = useAnalytics(adminAnalyticsApi.growth, range);
  const common = { loading, error, onRetry: reload, hasData: !!data };
  const days = data?.days ?? [];
  const daily = days.map((day, i) => ({ day, signups: data!.signups[i], dau: data!.dau[i], wau: data!.wau[i] }));

  const first = data?.funnel[0]?.count ?? 0;
  const last = data?.funnel.at(-1)?.count ?? 0;
  const funnelRows: BarRow[] = (data?.funnel ?? []).map((s, i) => ({
    key: s.key, label: s.label, value: s.count, color: ORDINAL[Math.min(i, ORDINAL.length - 1)],
    valueLabel: first ? `${fmtInt(s.count)} · ${fmtPct(s.count / first)}` : fmtInt(s.count),
  }));

  const slots = (data?.heatmap ?? []).flatMap((row, d) => row.map((count, h) => ({ d, h, count }))).filter((s) => s.count > 0)
    .sort((a, b) => b.count - a.count);
  const peak = slots[0];
  const mix = (items: Array<{ key: string; count: number }>, unit: string): BarRow[] =>
    items.map((g) => ({ key: g.key, label: `${unit} ${g.key}`, value: g.count }));

  return (
    <Section id="khoi-tang-truong" title="Tăng trưởng và giữ chân" description="Học sinh đến từ đâu, có quay lại không và học vào lúc nào.">
      <ChartCard
        {...common} hasData={!!data && sum(data.signups) + sum(data.dau) > 0}
        title={data ? `${fmtInt(sum(data.signups))} học sinh đăng ký mới trong ${range} ngày` : 'Đăng ký mới theo ngày'}
        description="Số tài khoản học sinh tạo mỗi ngày"
        table={{ columns: ['Ngày', 'Đăng ký mới'], rows: daily.map((d) => [shortDay(d.day), d.signups]) }}
      >
        <TrendChart data={daily} xKey="day" xFormat={shortDay} series={[{ key: 'signups', label: 'Đăng ký mới', color: CHART.s1 }]} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && sum(data.dau) > 0}
        title={data ? `Trung bình ${fmtInt(Math.round(sum(data.dau) / Math.max(1, data.dau.length)))} học sinh hoạt động mỗi ngày` : 'Học sinh hoạt động'}
        description={data?.stickiness != null ? `Mỗi ngày có ${fmtPct(data.stickiness)} số học sinh hoạt động trong kỳ quay lại. Hoạt động = đăng nhập hoặc bắt đầu làm bài.` : 'Hoạt động = đăng nhập hoặc bắt đầu làm bài.'}
        legend={[{ label: 'Trong ngày', color: CHART.s1 }, { label: 'Trong 7 ngày gần nhất', color: CHART.s2 }]}
        table={{ columns: ['Ngày', 'Trong ngày', 'Trong 7 ngày'], rows: daily.map((d) => [shortDay(d.day), d.dau, d.wau]) }}
      >
        <TrendChart data={daily} xKey="day" xFormat={shortDay} series={[{ key: 'dau', label: 'Trong ngày', color: CHART.s1 }, { key: 'wau', label: 'Trong 7 ngày gần nhất', color: CHART.s2 }]} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && first > 0}
        title={first ? `${fmtPct(last / first)} học sinh đăng ký đã làm bài đầu tiên` : 'Phễu kích hoạt'}
        description={`Chỉ tính ${fmtInt(first)} học sinh đăng ký trong kỳ; mỗi bước chỉ đếm người đã qua bước trước.`}
        emptyText="Chưa có học sinh đăng ký trong khoảng này."
        table={{ columns: ['Bước', 'Học sinh', 'So với đăng ký'], rows: (data?.funnel ?? []).map((s) => [s.label, s.count, first ? fmtPct(s.count / first) : '—']) }}
      >
        <BarList rows={funnelRows} max={first} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && slots.length > 0}
        title={peak ? `Đông nhất: ${WEEKDAYS[peak.d]}, ${peak.h}–${peak.h + 1} giờ` : 'Giờ học cao điểm'}
        description="Số bài làm bắt đầu theo thứ và giờ (giờ Việt Nam)"
        emptyText="Chưa có bài làm nào trong khoảng này."
        table={{ columns: ['Thứ', 'Giờ', 'Số bài'], rows: slots.slice(0, 15).map((s) => [WEEKDAYS[s.d], `${s.h}–${s.h + 1}h`, s.count]) }}
      >
        <HourHeatmap grid={data?.heatmap ?? []} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && sum(data.grades.map((g) => g.count)) > 0}
        title="Cơ cấu học sinh theo khối và mục tiêu"
        description="Từ hồ sơ học sinh đã hoàn tất, tính toàn bộ không theo khoảng thời gian"
        className="lg:col-span-2"
        table={{ columns: ['Nhóm', 'Học sinh'], rows: [...(data?.grades ?? []).map((g) => [`Khối ${g.key}`, g.count]), ...(data?.targets ?? []).map((t) => [`Mục tiêu ${t}`, t.count])] }}
      >
        <div className="grid gap-6 sm:grid-cols-2">
          <BarList rows={mix(data?.grades ?? [], 'Khối')} />
          <BarList rows={mix(data?.targets ?? [], 'Mục tiêu')} color={CHART.s2} />
        </div>
      </ChartCard>
    </Section>
  );
}

// ---- B. Học tập và điểm số --------------------------------------------------------------------------------

export function LearningSection({ range }: { range: RangeDays }) {
  const { data, error, loading, reload } = useAnalytics(adminAnalyticsApi.learning, range);
  const common = { loading, error, onRetry: reload, hasData: !!data && data.graded > 0, emptyText: 'Chưa có bài làm nào được chấm trong khoảng này.' };
  const weekly = data?.weekly ?? [];
  const lastScored = [...weekly].reverse().find((w) => w.average !== null);
  const outcomes = data?.outcomes ?? [];
  const timeout = sum(outcomes.map((o) => o.timeout));
  const finished = timeout + sum(outcomes.map((o) => o.manual));
  const weakest = data?.chapters[0];

  return (
    <Section id="khoi-hoc-tap" title="Học tập và điểm số" description="Học sinh làm bài tốt đến đâu và yếu ở chương nào.">
      <ChartCard
        {...common}
        title={data?.median != null ? `Điểm trung vị ${fmtScore(data.median)}, trung bình ${fmtScore(data.average ?? 0)} trên ${fmtInt(data.graded)} bài` : 'Phân bố điểm'}
        description="Số bài theo từng khoảng 1 điểm, thang 10"
        table={{ columns: ['Khoảng điểm', 'Số bài'], rows: (data?.bins ?? []).map((b) => [b.label, b.count]) }}
      >
        <ColumnsChart data={data?.bins ?? []} xKey="label" series={[{ key: 'count', label: 'Số bài', color: CHART.s1 }]} />
      </ChartCard>

      <ChartCard
        {...common}
        title={lastScored ? `Tuần gần nhất có điểm: trung bình ${fmtScore(lastScored.average ?? 0)} trên ${lastScored.attempts} bài` : 'Điểm theo tuần'}
        description="Hai biểu đồ cùng trục thời gian, mỗi biểu đồ một đại lượng"
        table={{ columns: ['Tuần', 'Số bài', 'Điểm trung bình'], rows: weekly.map((w) => [weekLabel(w.week), w.attempts, w.average === null ? '—' : fmtScore(w.average)]) }}
      >
        <div className="grid gap-3">
          <p className="text-caption text-muted-foreground">Số bài đã chấm mỗi tuần</p>
          <ColumnsChart data={weekly} xKey="week" xFormat={weekLabel} height={110} series={[{ key: 'attempts', label: 'Số bài', color: CHART.s1 }]} />
          <p className="text-caption text-muted-foreground">Điểm trung bình mỗi tuần</p>
          <TrendChart data={weekly} xKey="week" xFormat={weekLabel} height={130} yDomain={[0, 10]} yTicks={[0, 5, 10]} valueFormat={fmtScore} series={[{ key: 'average', label: 'Điểm trung bình', color: CHART.s1 }]} />
        </div>
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && finished > 0}
        title={finished ? `${fmtPct(timeout / finished)} bài kết thúc vì hết giờ` : 'Cách kết thúc bài'}
        description="Bài học sinh nộp, bài hết giờ tự nộp và bài đang làm dở, theo tuần bắt đầu"
        legend={[{ label: 'Học sinh nộp', color: CHART.s1 }, { label: 'Hết giờ', color: CHART.s2 }, { label: 'Đang làm', color: CHART.s3 }]}
        table={{ columns: ['Tuần', 'Học sinh nộp', 'Hết giờ', 'Đang làm'], rows: outcomes.map((o) => [weekLabel(o.week), o.manual, o.timeout, o.in_progress]) }}
      >
        <ColumnsChart stacked data={outcomes} xKey="week" xFormat={weekLabel} series={[{ key: 'manual', label: 'Học sinh nộp', color: CHART.s1 }, { key: 'timeout', label: 'Hết giờ', color: CHART.s2 }, { key: 'in_progress', label: 'Đang làm', color: CHART.s3 }]} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && data.chapters.length > 0}
        title={weakest ? `Yếu nhất: ${weakest.name} (${fmtPct(weakest.rate)} câu đúng)` : 'Chương có tỉ lệ đúng thấp nhất'}
        description={data ? `Tối đa ${10} chương thấp nhất. ${data.chapters_hidden ? `${data.chapters_hidden} chương dưới ${data.min_answers} câu làm chưa xếp hạng vì mẫu quá nhỏ.` : ''}` : undefined}
        emptyText="Chưa chương nào đủ số câu làm để xếp hạng."
        table={{ columns: ['Chương', 'Đúng', 'Tổng', 'Tỉ lệ đúng'], rows: (data?.chapters ?? []).map((c) => [`${c.code} ${c.name}`, c.correct, c.total, fmtPct(c.rate)]) }}
      >
        <BarList max={1} rows={(data?.chapters ?? []).map((c) => ({ key: c.code, label: `${c.code} · ${c.name}`, value: c.rate, valueLabel: fmtPct(c.rate), hint: `${c.correct}/${c.total} câu đúng` }))} />
      </ChartCard>
    </Section>
  );
}

// ---- C. Ngân hàng câu hỏi ---------------------------------------------------------------------------------

export function BankSection({ range }: { range: RangeDays }) {
  const { data, error, loading, reload } = useAnalytics(adminAnalyticsApi.bank, range);
  const common = { loading, error, onRetry: reload };
  const total = data ? data.published + data.draft + data.private + data.archived : 0;
  const rows = data?.coverage ?? [];
  const zeroCells = rows.reduce((n, r) => n + Object.values(r.counts).filter((c) => c === 0).length, 0);
  const shortages = data?.shortages;
  const missing = shortages?.chapters ?? [];

  return (
    <Section id="khoi-ngan-hang" title="Ngân hàng câu hỏi" description="Còn thiếu câu ở đâu và học sinh đang cần gì mà ngân hàng chưa có.">
      <ChartCard
        {...common} hasData={total > 0}
        title={data ? `${fmtInt(data.published)} câu dùng được, ${fmtInt(data.draft)} câu nháp chờ duyệt` : 'Trạng thái câu hỏi'}
        description="Câu đã đăng chia theo độ khó ở bên dưới"
        legend={[{ label: 'Đã đăng', color: CHART.s1 }, { label: 'Nháp', color: CHART.s2 }, { label: 'Riêng tư', color: CHART.s3 }, { label: 'Lưu trữ', color: CHART.axis }]}
        table={{ columns: ['Nhóm', 'Số câu'], rows: [['Đã đăng', data?.published ?? 0], ['Nháp', data?.draft ?? 0], ['Riêng tư', data?.private ?? 0], ['Lưu trữ', data?.archived ?? 0], ...(data?.by_difficulty ?? []).map((d) => [`Độ khó ${d.key}`, d.count])] }}
      >
        <div className="grid gap-5">
          <SegmentedBar label="Trạng thái câu hỏi" parts={[
            { key: 'published', label: 'Đã đăng', value: data?.published ?? 0, color: CHART.s1 },
            { key: 'draft', label: 'Nháp', value: data?.draft ?? 0, color: CHART.s2 },
            { key: 'private', label: 'Riêng tư', value: data?.private ?? 0, color: CHART.s3 },
            { key: 'archived', label: 'Lưu trữ', value: data?.archived ?? 0, color: CHART.axis },
          ]} />
          <BarList rows={(data?.by_difficulty ?? []).map((d) => ({ key: d.key, label: `Độ khó ${d.key}`, value: d.count }))} />
        </div>
      </ChartCard>

      <ChartCard
        {...common} hasData={rows.length > 0}
        title={zeroCells ? `${zeroCells} ô chương × độ khó chưa có câu nào` : 'Mọi chương đều có câu ở cả bốn mức độ khó'}
        description="Chỉ đếm câu đã đăng. Ô vàng là chỗ cần soạn thêm; ô xanh càng đậm càng nhiều câu."
        emptyText="Chưa có chương nào trong danh mục."
      >
        <CoverageMatrix rows={rows} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!shortages && shortages.drafts > 0}
        className="lg:col-span-2"
        title={shortages ? `${shortages.drafts_with_shortage}/${shortages.drafts} đề nháp trong ${range} ngày bị thiếu câu` : 'Chương học sinh cần mà thiếu câu'}
        description="Số câu còn thiếu cộng dồn theo chương gốc, lấy từ các đề học sinh vừa yêu cầu. Soạn thêm ở đầu danh sách trước."
        emptyText="Chưa có đề nháp nào được tạo trong khoảng này."
        table={{ columns: ['Chương', 'Câu còn thiếu', 'Số lần thiếu'], rows: missing.map((c) => [`${c.code} ${c.name}`, c.missing, c.occurrences]) }}
      >
        {missing.length === 0 ? (
          <p className="rounded-xl bg-success-subtle px-4 py-3 text-label text-success">Mọi đề nháp trong khoảng này đều đủ câu.</p>
        ) : (
          <BarList color={CHART.s2} rows={missing.map((c) => ({ key: c.code, label: `${c.code} · ${c.name}`, value: c.missing, valueLabel: `${fmtInt(c.missing)} câu`, hint: `Thiếu trong ${c.occurrences} lần dựng đề` }))} />
        )}
      </ChartCard>
    </Section>
  );
}

// ---- D. Vận hành ------------------------------------------------------------------------------------------

export function OperationsSection({ range }: { range: RangeDays }) {
  const { data, error, loading, reload } = useAnalytics(adminAnalyticsApi.operations, range);
  const common = { loading, error, onRetry: reload };
  const days = data?.days ?? [];
  const imports = data?.imports;
  const daily = days.map((day, i) => ({
    day, completed: imports?.completed[i] ?? 0, failed: imports?.failed[i] ?? 0, in_flight: imports?.in_flight[i] ?? 0,
    granted: data?.credits.granted[i] ?? 0, spent: data?.credits.spent[i] ?? 0,
  }));
  const chat = data?.chat;
  const failedStages = imports?.failed_by_stage ?? [];

  return (
    <Section id="khoi-van-hanh" title="Vận hành" description="Hệ thống có chạy ổn không: nhập đề PDF, credit và luồng tạo đề.">
      <OnlineStudentsCard />

      <ChartCard
        {...common} hasData={!!imports && imports.total > 0}
        title={imports?.success_rate != null ? `${fmtPct(imports.success_rate)} lượt nhập đề PDF thành công` : 'Nhập đề PDF'}
        description={failedStages.length ? `Lỗi xảy ra ở bước: ${failedStages.map((s) => `${s.key} (${s.count})`).join(', ')}` : 'Lượt nhập theo ngày tạo'}
        emptyText="Chưa có lượt nhập đề PDF trong khoảng này."
        legend={[{ label: 'Xong', color: CHART.s1 }, { label: 'Lỗi', color: CHART.s2 }, { label: 'Đang xử lý', color: CHART.s3 }]}
        table={{ columns: ['Ngày', 'Xong', 'Lỗi', 'Đang xử lý'], rows: daily.map((d) => [shortDay(d.day), d.completed, d.failed, d.in_flight]) }}
      >
        <ColumnsChart stacked data={daily} xKey="day" xFormat={shortDay} series={[{ key: 'completed', label: 'Xong', color: CHART.s1 }, { key: 'failed', label: 'Lỗi', color: CHART.s2 }, { key: 'in_flight', label: 'Đang xử lý', color: CHART.s3 }]} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!data && sum(data.credits.granted) + sum(data.credits.spent) > 0}
        title={data ? `Đã cấp ${fmtInt(sum(data.credits.granted))} credit, học sinh tiêu ${fmtInt(sum(data.credits.spent))}` : 'Credit cấp và tiêu'}
        description="Credit học sinh nhận và dùng để tạo đề mỗi ngày"
        emptyText="Chưa có biến động credit trong khoảng này."
        legend={[{ label: 'Cấp', color: CHART.s1 }, { label: 'Tiêu', color: CHART.s2 }]}
        table={{ columns: ['Ngày', 'Cấp', 'Tiêu'], rows: daily.map((d) => [shortDay(d.day), d.granted, d.spent]) }}
      >
        <TrendChart data={daily} xKey="day" xFormat={shortDay} series={[{ key: 'granted', label: 'Cấp', color: CHART.s1 }, { key: 'spent', label: 'Tiêu', color: CHART.s2 }]} />
      </ChartCard>

      <ChartCard
        {...common} hasData={!!chat && chat.sessions > 0}
        title={chat?.sessions ? `${fmtPct(chat.with_attempt / chat.sessions)} phiên chat tạo đề đi tới làm bài` : 'Từ chat tới làm bài'}
        description="Phiên chat tạo đề mở trong kỳ; mỗi bước chỉ đếm phiên đã qua bước trước"
        emptyText="Chưa có phiên chat tạo đề nào trong khoảng này."
        table={{ columns: ['Bước', 'Số phiên'], rows: [['Mở phiên chat', chat?.sessions ?? 0], ['Có đề nháp', chat?.with_draft ?? 0], ['Có làm bài', chat?.with_attempt ?? 0]] }}
      >
        <BarList max={chat?.sessions} rows={[
          { key: 'sessions', label: 'Mở phiên chat', value: chat?.sessions ?? 0, color: ORDINAL[0] },
          { key: 'drafts', label: 'Có đề nháp', value: chat?.with_draft ?? 0, color: ORDINAL[2] },
          { key: 'attempts', label: 'Có làm bài', value: chat?.with_attempt ?? 0, color: ORDINAL[4] },
        ]} />
      </ChartCard>
    </Section>
  );
}
