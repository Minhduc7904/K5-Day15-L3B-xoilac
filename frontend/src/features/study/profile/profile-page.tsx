'use client';

import {
  Award,
  CalendarCheck,
  CalendarDays,
  Coins,
  Flame as FlameIcon,
  GraduationCap,
  Mail,
  Medal,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  School,
  Star,
  Target,
  Trophy,
} from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import Image from 'next/image';
import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { cn } from '@/lib/cn';
import { mockMode } from '@/lib/config';
import { studyApi } from '../api';
import { Flame } from '../components/flame';
import { ErrorState, PageContainer } from '../components/page-states';
import { formatDuration, longDate, relativeDay } from '../format';
import { formatScore } from '../grading';
import type { CreditSummary, DashboardData, StudentProfile } from '../types';
import { useResource } from '../use-resource';

const TABS = [
  { id: 'activity', label: 'Hoạt động' },
  { id: 'credit', label: 'Credit' },
  { id: 'settings', label: 'Cài đặt' },
] as const;
type Tab = (typeof TABS)[number]['id'];
const hashTab: Record<string, Tab> = { '#credit': 'credit', '#settings': 'settings' };

const card = 'rounded-2xl bg-background p-5 shadow-soft';

export function ProfilePage() {
  const res = useResource(() => studyApi.getProfile(), 'profile');
  const credits = useResource(() => studyApi.getCredits(), 'profile-credits');

  return (
    <div className="min-h-[calc(100dvh-var(--student-header-height))] bg-surface">
      <PageContainer className="grid grid-cols-[minmax(0,1fr)] gap-5 pt-4 lg:pt-6">
        {res.status === 'loading' && (
          <div className="grid gap-5">
            <Skeleton className="h-80 rounded-3xl" />
            <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
              <Skeleton className="h-72 rounded-2xl" />
              <Skeleton className="h-72 rounded-2xl" />
            </div>
          </div>
        )}
        {res.status === 'error' && <ErrorState onRetry={res.reload} />}
        {res.status === 'ready' && (
          <Profile initial={res.data.profile} dashboard={res.data.dashboard} credits={credits.status === 'ready' ? credits.data : null} />
        )}
      </PageContainer>
    </div>
  );
}

function Profile({ initial, dashboard, credits }: { initial: StudentProfile; dashboard: DashboardData; credits: CreditSummary | null }) {
  const [profile, setProfile] = useState(initial);
  const [tab, setTab] = useState<Tab>('activity');

  // Mở thẳng tab theo #credit / #settings (vd bấm số credit trên thanh đầu trang).
  useEffect(() => {
    const sync = () => {
      const next = hashTab[window.location.hash];
      if (next) setTab(next);
    };
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);

  const select = (next: Tab) => {
    setTab(next);
    window.history.replaceState(null, '', next === 'activity' ? '/profile' : `/profile#${next}`);
  };

  return (
    <>
      <Cover profile={profile} dashboard={dashboard} credits={credits} tab={tab} onTab={select} />

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-5 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:sticky lg:top-[calc(var(--student-header-height)+1.25rem)]">
          <Intro profile={profile} onEdit={() => select('settings')} />
          <CreditMini credits={credits} onOpen={() => select('credit')} />
          <Achievements dashboard={dashboard} />
        </aside>

        <div id="profile-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="grid grid-cols-[minmax(0,1fr)] gap-5">
          {tab === 'activity' && (
            <>
              <WeeklyGoal days={dashboard.streak.days} target={profile.weeklyTarget} />
              <Heatmap days={dashboard.streak.days} current={dashboard.streak.current} best={dashboard.streak.best} />
              <Totals dashboard={dashboard} />
            </>
          )}
          {tab === 'credit' && <CreditPanel credits={credits} />}
          {tab === 'settings' && (
            <>
              <ProfileForm profile={profile} onSaved={setProfile} />
              {mockMode && <ResetMock />}
            </>
          )}
        </div>
      </div>
    </>
  );
}

/* ---------------- Ảnh bìa, ảnh đại diện, tab ---------------- */

function Cover({ profile, dashboard, credits, tab, onTab }: {
  profile: StudentProfile;
  dashboard: DashboardData;
  credits: CreditSummary | null;
  tab: Tab;
  onTab: (t: Tab) => void;
}) {
  const reduce = useReducedMotion();
  const initial = profile.name.trim().charAt(0).toLocaleUpperCase('vi') || '?';

  return (
    <section aria-labelledby="profile-name-title" className="overflow-hidden rounded-3xl bg-background shadow-soft">
      <div className="relative isolate h-36 overflow-hidden bg-primary sm:h-48">
        <div aria-hidden="true" className="bg-grid-inverse absolute inset-0 -z-10" />
        <div aria-hidden="true" className="absolute -right-10 -bottom-24 -z-10 size-72 rounded-full bg-accent/25 blur-2xl" />
        <motion.div
          aria-hidden="true"
          className="absolute right-6 bottom-0 w-24 sm:right-10 sm:w-32"
          initial={reduce ? false : { y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <Image src="/brand/mascot/static/studying.webp" alt="" width={192} height={192} unoptimized priority className="pixelated h-auto w-full" />
        </motion.div>
      </div>

      <div className="px-5 sm:px-8">
        <div className="flex flex-col gap-x-5 gap-y-3 sm:flex-row sm:flex-wrap sm:items-end">
          <span
            aria-hidden="true"
            className="relative -mt-14 grid size-28 shrink-0 place-items-center rounded-full bg-primary-subtle text-[2.75rem] font-bold text-primary ring-[6px] ring-background sm:-mt-16 sm:size-36 sm:text-[3.5rem]"
          >
            {initial}
          </span>
          <div className="grid min-w-0 flex-1 gap-1 sm:min-w-[16rem] sm:pb-3">
            <h1 id="profile-name-title" className="text-h1 break-words text-foreground">{profile.name}</h1>
            <p className="flex flex-wrap gap-x-3 gap-y-1 text-label text-muted-foreground">
              <span><b className="font-semibold text-foreground tabular-nums">{dashboard.totals.exams}</b> đề đã làm</span>
              <span><b className="font-semibold text-foreground tabular-nums">{dashboard.streak.current}</b> ngày liên tiếp</span>
              {credits && <span><b className="font-semibold text-foreground tabular-nums">{credits.balance}</b> credit</span>}
            </p>
          </div>
          <div className="flex gap-2 sm:ml-auto sm:pb-3">
            <Button variant="secondary" leftIcon={<Pencil aria-hidden="true" />} onClick={() => onTab('settings')}>
              Chỉnh sửa hồ sơ
            </Button>
            <Button href="/exams/new" leftIcon={<Plus aria-hidden="true" />}>
              Tạo đề
            </Button>
          </div>
        </div>

        <div role="tablist" aria-label="Mục hồ sơ" className="mt-5 flex gap-1 border-t border-border">
          {TABS.map((t) => (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              role="tab"
              type="button"
              aria-selected={tab === t.id}
              aria-controls="profile-panel"
              onClick={() => onTab(t.id)}
              className={cn(
                'relative min-h-12 px-4 text-label font-semibold transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
                tab === t.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
              {tab === t.id && <motion.span layoutId="profile-tab" className="absolute inset-x-2 bottom-0 h-[3px] rounded-t-full bg-primary" />}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- Cột trái ---------------- */

function Intro({ profile, onEdit }: { profile: StudentProfile; onEdit: () => void }) {
  const rows: Array<{ Icon: typeof Target; text: ReactNode }> = [
    { Icon: Target, text: <>Mục tiêu: <b className="font-semibold text-foreground">{profile.goal || 'chưa đặt'}</b></> },
    { Icon: School, text: <>Học tại <b className="font-semibold text-foreground">{profile.school || 'chưa nhập trường'}</b></> },
    { Icon: GraduationCap, text: <>Lớp <b className="font-semibold text-foreground">{profile.grade}</b></> },
    { Icon: Mail, text: <span className="break-all">{profile.email}</span> },
    { Icon: CalendarDays, text: <>Tham gia {longDate(profile.joinedAt)}</> },
  ];
  return (
    <section aria-labelledby="intro-title" className={card}>
      <h2 id="intro-title" className="mb-3 text-h3 text-foreground">Giới thiệu</h2>
      <ul className="grid gap-3">
        {rows.map(({ Icon, text }, i) => (
          <li key={i} className="flex items-start gap-3 text-label text-muted-foreground">
            <Icon className="mt-0.5 size-4.5 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span className="min-w-0">{text}</span>
          </li>
        ))}
      </ul>
      <Button variant="secondary" fullWidth className="mt-4" onClick={onEdit}>
        Sửa chi tiết
      </Button>
    </section>
  );
}

function CreditMini({ credits, onOpen }: { credits: CreditSummary | null; onOpen: () => void }) {
  if (!credits) return <Skeleton className="h-32 rounded-2xl" />;
  const ratio = credits.balance / credits.monthlyQuota;
  return (
    <section aria-labelledby="credit-mini-title" className={card}>
      <div className="flex items-center justify-between gap-3">
        <h2 id="credit-mini-title" className="text-h3 text-foreground">Credit</h2>
        <button type="button" onClick={onOpen} className="rounded-sm text-label font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          Chi tiết
        </button>
      </div>
      <p className="mt-2 flex items-baseline gap-1.5">
        <Coins className="size-5 self-center text-warning" aria-hidden="true" />
        <b className="text-h2 font-bold text-foreground tabular-nums">{credits.balance}</b>
        <span className="text-label text-muted-foreground">/ {credits.monthlyQuota} còn lại</span>
      </p>
      <Meter ratio={ratio} low={credits.balance < 100} className="mt-2" label="Credit còn lại" />
      <p className="mt-2 text-caption text-muted-foreground">Làm mới ngày {new Date(credits.resetsAt).toLocaleDateString('vi-VN')}</p>
    </section>
  );
}

function Achievements({ dashboard }: { dashboard: DashboardData }) {
  const bestScore = dashboard.scores.length ? Math.max(...dashboard.scores.map((s) => s.score)) : 0;
  const items = [
    { Icon: Star, title: 'Đề đầu tiên', desc: 'Nộp bài lần đầu', done: dashboard.scores.length >= 1 },
    { Icon: FlameIcon, title: 'Giữ lửa 7 ngày', desc: 'Chuỗi 7 ngày liên tục', done: dashboard.streak.best >= 7 },
    { Icon: Trophy, title: 'Chạm mốc 8', desc: 'Một đề đạt từ 8 điểm', done: bestScore >= 8 },
    { Icon: Medal, title: 'Điểm 9+', desc: 'Một đề đạt từ 9 điểm', done: bestScore >= 9 },
    { Icon: CalendarCheck, title: 'Chăm chỉ', desc: 'Làm 10 đề', done: dashboard.scores.length >= 10 },
    { Icon: Award, title: 'Học 10 giờ', desc: 'Tổng thời gian làm bài', done: dashboard.totals.minutes >= 600 },
  ];
  const doneCount = items.filter((i) => i.done).length;

  return (
    <section aria-labelledby="badge-title" className={card}>
      <div className="mb-3 flex items-baseline justify-between">
        <h2 id="badge-title" className="text-h3 text-foreground">Huy hiệu</h2>
        <span className="text-caption font-semibold text-muted-foreground tabular-nums">{doneCount}/{items.length} đã mở</span>
      </div>
      <ul className="grid grid-cols-3 gap-2">
        {items.map((b) => (
          <li
            key={b.title}
            title={`${b.title}: ${b.done ? 'đã đạt' : b.desc}`}
            className={cn('grid justify-items-center gap-1.5 rounded-xl px-1 py-3 text-center', b.done ? 'bg-flame-subtle' : 'bg-surface')}
          >
            <span className={cn('flex size-10 items-center justify-center rounded-full', b.done ? 'bg-flame text-primary-foreground' : 'bg-surface-muted text-muted-foreground')}>
              <b.Icon className="size-5" aria-hidden="true" />
            </span>
            <span className={cn('text-[0.6875rem] leading-tight font-semibold', b.done ? 'text-foreground' : 'text-muted-foreground')}>{b.title}</span>
            <span className="sr-only">{b.done ? 'Đã đạt' : `Chưa đạt: ${b.desc}`}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ---------------- Tab Hoạt động ---------------- */

function WeeklyGoal({ days, target }: { days: DashboardData['streak']['days']; target: number }) {
  const thisWeek = Math.min(days.slice(-7).filter((d) => d.studied).length, 7);
  const reached = thisWeek >= target;
  return (
    <section aria-labelledby="week-title" className={card}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 id="week-title" className="text-h3 text-foreground">Mục tiêu tuần này</h2>
          <p className="text-caption text-muted-foreground">Học ít nhất {target} ngày trong 7 ngày gần nhất</p>
        </div>
        <p className="text-h2 font-bold text-foreground tabular-nums">
          {thisWeek}<span className="text-body font-semibold text-muted-foreground">/{target}</span>
        </p>
      </div>
      <div className="mt-3 flex gap-1.5" aria-hidden="true">
        {Array.from({ length: target }, (_, i) => (
          <motion.span
            key={i}
            className={cn('h-3 flex-1 rounded-full', i < thisWeek ? 'bg-flame' : 'bg-surface-muted')}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ delay: 0.1 + i * 0.06 }}
            style={{ originX: 0 }}
          />
        ))}
      </div>
      <p className={cn('mt-3 text-label', reached ? 'font-semibold text-success' : 'text-muted-foreground')}>
        {reached ? 'Đã đạt mục tiêu tuần. Giỏi quá!' : `Còn ${target - thisWeek} ngày nữa là đạt mục tiêu tuần.`}
      </p>
    </section>
  );
}

function Heatmap({ days, current, best }: { days: DashboardData['streak']['days']; current: number; best: number }) {
  // Xếp theo cột tuần (T2 → CN), bắt đầu từ thứ Hai của tuần đầu.
  const first = new Date(days[0].date);
  const pad = (first.getDay() + 6) % 7;
  const cells: Array<(typeof days)[number] | null> = [...Array.from({ length: pad }, () => null), ...days];
  const weeks: Array<typeof cells> = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const total = days.filter((d) => d.studied).length;

  return (
    <section aria-labelledby="heat-title" className={card}>
      <div className="mb-4 flex items-center gap-3">
        <Flame size={32} lit={current > 0} />
        <div>
          <h2 id="heat-title" className="text-h3 text-foreground">Lịch học 12 tuần</h2>
          <p className="text-caption text-muted-foreground">
            {total} ngày có học · chuỗi hiện tại {current} ngày · dài nhất {best} ngày
          </p>
        </div>
      </div>
      <div className="overflow-x-auto pb-1 [scrollbar-width:thin]">
        <div className="flex w-fit gap-1.5">
          <div className="grid grid-rows-7 gap-1.5 pr-1 text-[0.625rem] text-muted-foreground" aria-hidden="true">
            {['T2', '', 'T4', '', 'T6', '', 'CN'].map((d, i) => (
              <span key={i} className="flex h-4 items-center sm:h-5">{d}</span>
            ))}
          </div>
          {weeks.map((week, w) => (
            <div key={w} className="grid grid-rows-7 gap-1.5">
              {week.map((day, d) =>
                day ? (
                  <span
                    key={day.date}
                    title={`${new Date(day.date).toLocaleDateString('vi-VN')}: ${day.studied ? 'có học' : 'chưa học'}`}
                    className={cn(
                      'size-4 rounded-[5px] sm:size-5',
                      day.studied ? 'bg-flame' : 'bg-surface-muted',
                      w === weeks.length - 1 && d === week.length - 1 && 'ring-2 ring-foreground ring-offset-1 ring-offset-background',
                    )}
                  />
                ) : (
                  <span key={`pad-${d}`} className="size-4 sm:size-5" />
                ),
              )}
            </div>
          ))}
        </div>
      </div>
      <p className="sr-only">
        Trong 12 tuần gần nhất bạn học {total} ngày. Chuỗi hiện tại {current} ngày, dài nhất {best} ngày.
      </p>
    </section>
  );
}

function Totals({ dashboard }: { dashboard: DashboardData }) {
  const bestScore = dashboard.scores.length ? Math.max(...dashboard.scores.map((s) => s.score)) : 0;
  return (
    <p className="px-1 text-caption text-muted-foreground">
      Tổng: {dashboard.scores.length} lượt làm bài · {formatDuration(dashboard.totals.minutes * 60)} · cao nhất {formatScore(bestScore)} điểm
    </p>
  );
}

/* ---------------- Tab Credit ---------------- */

function CreditPanel({ credits }: { credits: CreditSummary | null }) {
  if (!credits) return <Skeleton className="h-80 rounded-2xl" />;
  const reset = new Date(credits.resetsAt).toLocaleDateString('vi-VN');
  return (
    <>
      <section id="credit" aria-labelledby="credit-title" className={cn(card, 'grid gap-4 sm:p-6')}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="credit-title" className="text-h3 text-foreground">Credit tạo đề</h2>
            <p className="text-caption text-muted-foreground">Mỗi lần agent dựng một đề trừ 1 credit. Làm bài, làm lại đề cũ không tốn credit.</p>
          </div>
          <p className="flex items-baseline gap-1.5">
            <Coins className="size-6 self-center text-warning" aria-hidden="true" />
            <b className="text-display leading-none font-bold text-foreground tabular-nums">{credits.balance}</b>
            <span className="text-body text-muted-foreground">/ {credits.monthlyQuota}</span>
          </p>
        </div>
        <Meter ratio={credits.balance / credits.monthlyQuota} low={credits.balance < 100} label="Credit còn lại" thick />
        <dl className="grid grid-cols-3 gap-3 text-center">
          {[
            { k: 'Hạn mức tháng', v: credits.monthlyQuota },
            { k: 'Đã dùng tháng này', v: credits.usedThisMonth },
            { k: 'Làm mới', v: reset },
          ].map(({ k, v }) => (
            <div key={k} className="rounded-xl bg-surface px-2 py-3">
              <dt className="text-caption text-muted-foreground">{k}</dt>
              <dd className="text-body-lg font-bold text-foreground tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
        {mockMode && <p className="text-caption text-muted-foreground">Bản mock: số dư tính từ các đề AI bạn đã tạo trong tháng, hạn mức 500 là số tự đặt.</p>}
      </section>

      <section aria-labelledby="ledger-title" className={card}>
        <h2 id="ledger-title" className="mb-2 text-h3 text-foreground">Lịch sử credit</h2>
        <ol className="divide-y divide-border">
          {credits.history.map((h) => (
            <li key={h.id} className="flex items-center gap-3 py-2.5">
              <span className={cn('grid size-9 shrink-0 place-items-center rounded-full', h.amount > 0 ? 'bg-success-subtle text-success' : 'bg-surface text-muted-foreground')}>
                {h.amount > 0 ? <Plus className="size-4" aria-hidden="true" /> : <Coins className="size-4" aria-hidden="true" />}
              </span>
              <span className="grid min-w-0 flex-1">
                <span className="truncate text-label font-medium text-foreground">{h.label}</span>
                <span className="text-caption text-muted-foreground">{relativeDay(h.date)}</span>
              </span>
              <span className={cn('text-label font-bold tabular-nums', h.amount > 0 ? 'text-success' : 'text-foreground')}>
                {h.amount > 0 ? `+${h.amount}` : h.amount}
              </span>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}

function Meter({ ratio, label, className, thick, low }: { ratio: number; label: string; className?: string; thick?: boolean; low?: boolean }) {
  const pct = Math.round(Math.max(0, Math.min(1, ratio)) * 100);
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      className={cn('overflow-hidden rounded-full bg-surface-muted', thick ? 'h-3' : 'h-2', className)}
    >
      <motion.div
        className={cn('h-full rounded-full', low ? 'bg-muted-foreground' : 'bg-ember')}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

/* ---------------- Tab Cài đặt ---------------- */

function ProfileForm({ profile, onSaved }: { profile: StudentProfile; onSaved: (p: StudentProfile) => void }) {
  const [values, setValues] = useState(profile);
  const [errors, setErrors] = useState<{ name?: string }>({});
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const dirty = JSON.stringify(values) !== JSON.stringify(profile);

  useEffect(() => setValues(profile), [profile]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!values.name.trim()) {
      setErrors({ name: 'Nhập tên hiển thị của bạn.' });
      document.getElementById('profile-name')?.focus();
      return;
    }
    setErrors({});
    setSaving(true);
    try {
      const saved = await studyApi.updateProfile({ ...values, name: values.name.trim() });
      onSaved(saved);
      toast({ tone: 'success', title: 'Đã lưu hồ sơ' });
    } catch {
      toast({ tone: 'danger', title: 'Chưa lưu được', description: 'Thử lại sau nhé.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-labelledby="form-title" className={cn(card, 'grid gap-5 sm:p-6')}>
      <h2 id="form-title" className="text-h3 text-foreground">Thông tin & cài đặt</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Tên hiển thị" required error={errors.name} id="profile-name">
          {(field) => <Input {...field} autoComplete="nickname" value={values.name} onChange={(e) => setValues({ ...values, name: e.target.value })} />}
        </FormField>
        <FormField label="Lớp">
          {({ id, 'aria-describedby': describedBy }) => (
            <select
              id={id}
              aria-describedby={describedBy}
              value={values.grade}
              onChange={(e) => setValues({ ...values, grade: Number(e.target.value) as StudentProfile['grade'] })}
              className="h-11 w-full rounded-xl border border-input bg-background px-3 text-body text-foreground outline-none focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20"
            >
              {[10, 11, 12].map((g) => (
                <option key={g} value={g}>Lớp {g}</option>
              ))}
            </select>
          )}
        </FormField>
        <FormField label="Trường">
          {(field) => <Input {...field} autoComplete="organization" value={values.school} onChange={(e) => setValues({ ...values, school: e.target.value })} />}
        </FormField>
        <FormField label="Mục tiêu">
          {(field) => <Input {...field} value={values.goal} placeholder="Vd: Đạt 8+ môn Toán" onChange={(e) => setValues({ ...values, goal: e.target.value })} />}
        </FormField>
      </div>

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-label font-semibold text-foreground">Số ngày học mỗi tuần</legend>
        <div className="flex flex-wrap gap-1.5">
          {[2, 3, 4, 5, 6, 7].map((n) => (
            <label
              key={n}
              className={cn(
                'flex size-11 cursor-pointer items-center justify-center rounded-xl border text-label font-bold transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring',
                values.weeklyTarget === n ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground hover:border-primary/50',
              )}
            >
              <input type="radio" name="weekly" className="sr-only" checked={values.weeklyTarget === n} onChange={() => setValues({ ...values, weeklyTarget: n })} />
              {n}
            </label>
          ))}
        </div>
      </fieldset>

      <Switch
        label="Nhắc học mỗi tối"
        description="Gửi lời nhắc lúc 20:00 nếu hôm đó bạn chưa học (chưa gửi thật ở bản mock)."
        checked={values.reminders}
        onCheckedChange={(v) => setValues({ ...values, reminders: v })}
      />

      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <Button type="submit" loading={saving} disabled={!dirty} leftIcon={<Save aria-hidden="true" />}>
          {saving ? 'Đang lưu…' : 'Lưu thay đổi'}
        </Button>
        {dirty && (
          <Button variant="ghost" onClick={() => setValues(profile)} disabled={saving}>
            Huỷ
          </Button>
        )}
      </div>
    </form>
  );
}

function ResetMock() {
  const [asking, setAsking] = useState(false);
  return (
    <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-dashed border-border p-5">
      <div className="grid gap-0.5">
        <h2 className="text-label font-semibold text-foreground">Dữ liệu mẫu (chế độ mock)</h2>
        <p className="text-caption text-muted-foreground">Xoá các đề, lượt làm bài và hồ sơ bạn tạo thêm, quay về dữ liệu ban đầu để demo lại.</p>
      </div>
      {asking ? (
        <div className="flex gap-2">
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              studyApi.resetMockData();
              window.location.assign('/dashboard');
            }}
          >
            Xoá và khôi phục
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setAsking(false)}>
            Huỷ
          </Button>
        </div>
      ) : (
        <Button variant="outline" size="sm" leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => setAsking(true)}>
          Khôi phục dữ liệu mẫu
        </Button>
      )}
    </section>
  );
}
