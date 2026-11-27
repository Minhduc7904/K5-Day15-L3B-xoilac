'use client';

import { isAxiosError } from 'axios';
import { useId, useState, type FormEvent, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { useLogout } from '@/features/auth/use-logout';
import { Switch } from '@/components/ui/checkbox';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/cn';
import { EXAM_PERIODS, type ExamPeriod, type StudentProfile } from './student-account-api';
import { useStudentAccount } from './student-account-provider';

const weekdays = [1, 2, 3, 4, 5, 6];
const selectClass = 'h-11 w-full rounded-xl border border-input bg-background px-3 text-body text-foreground outline-none focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20';

export function ProfileForm({ profile }: { profile?: StudentProfile }) {
  const account = useStudentAccount();
  const { leaving, logout } = useLogout();
  const id = useId();
  const [school, setSchool] = useState(profile?.school_name ?? '');
  const [displayName, setDisplayName] = useState(profile?.display_name ?? '');
  const [grade, setGrade] = useState(profile?.grade.toString() ?? '');
  const [target, setTarget] = useState(profile?.target_score.toString() ?? '');
  const [exam, setExam] = useState<ExamPeriod | ''>(profile?.exam_period ?? '');
  const [days, setDays] = useState(profile?.study_days ?? []);
  const [reminders, setReminders] = useState(Boolean(profile?.reminder_time));
  const [reminderTime, setReminderTime] = useState(profile?.reminder_time?.slice(0, 5) ?? '08:00');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string>();
  const [dayError, setDayError] = useState(false);
  const verified = account?.status?.email_verified === true;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(false);
    setError(undefined);
    setDayError(days.length === 0);
    if (!account || !exam || !days.length || saving) return;
    if (!school.trim()) {
      setError('Nhập tên trường của bạn.');
      return;
    }

    setSaving(true);
    try {
      await account.saveProfile({
        school_name: school.trim(), grade: Number(grade), target_score: Number(target),
        exam_period: exam, study_days: days,
        reminder_time: reminders ? reminderTime : null,
        ...(displayName.trim() ? { display_name: displayName.trim() } : {}),
      });
      setSaved(true);
    } catch (failure) {
      setError(isAxiosError(failure) && failure.response?.data?.code === 'REMINDER_EMAIL_UNVERIFIED'
        ? 'Hãy xác minh email trước khi bật nhắc học.'
        : 'Chưa lưu được hồ sơ. Kiểm tra thông tin và thử lại.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} onChange={() => setSaved(false)} className="grid gap-5 rounded-2xl bg-background p-5 shadow-soft sm:p-6">
      <fieldset disabled={saving} className="grid gap-5">
        {profile && (
          <FormField label="Tên hiển thị">
            {(field) => <Input {...field} value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="nickname" maxLength={100} />}
          </FormField>
        )}
        <FormField label="Trường đang học" required>
          {(field) => <Input {...field} required autoComplete="organization" maxLength={200} value={school} onChange={(event) => setSchool(event.target.value)} />}
        </FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <ProfileSelect label="Bạn đang học khối mấy?" value={grade} onChange={setGrade}>
            {[10, 11, 12].map((value) => <option key={value} value={value}>Lớp {value}</option>)}
          </ProfileSelect>
          <ProfileSelect label="Mục tiêu điểm Toán" value={target} onChange={setTarget}>
            {[7, 8, 9].map((value) => <option key={value} value={value}>{value}+</option>)}
          </ProfileSelect>
        </div>
        <ProfileSelect label="Kỳ thi bạn muốn ôn" value={exam} onChange={(value) => setExam(value as ExamPeriod | '')}>
          {Object.entries(EXAM_PERIODS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </ProfileSelect>
        <fieldset className="grid gap-2" aria-describedby={dayError ? id + '-days' : undefined}>
          <legend className="mb-2 text-label font-semibold">Ngày bạn muốn ôn luyện</legend>
          <div className="flex flex-wrap gap-2">
            {weekdays.map((day) => (
              <label key={day} className={cn(
                'grid size-11 cursor-pointer place-items-center rounded-xl border text-label font-bold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring',
                days.includes(day) ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground',
              )}>
                <input type="checkbox" className="sr-only" checked={days.includes(day)} onChange={(event) => {
                  const checked = event.target.checked;
                  setDayError(false);
                  setDays((current) => checked ? [...current, day].sort() : current.filter((value) => value !== day));
                }} />
                T{day + 1}
              </label>
            ))}
          </div>
          {dayError && <p id={id + '-days'} role="alert" className="text-caption text-danger">Chọn ít nhất một ngày ôn.</p>}
        </fieldset>
        <Switch
          label="Nhắc học qua email"
          description={verified ? 'Gửi vào các ngày ôn bạn chọn.' : 'Xác minh email để bật nhắc học.'}
          disabled={!verified}
          checked={reminders}
          onCheckedChange={(checked) => { setReminders(checked); setSaved(false); }}
        />
        {reminders && (
          <FormField label="Giờ gửi email (giờ Việt Nam)" required>
            {(field) => <Input {...field} type="time" required value={reminderTime} onChange={(event) => setReminderTime(event.target.value)} />}
          </FormField>
        )}
      </fieldset>
      {error && <Alert tone="danger" title={error} />}
      {saved && profile && <p role="status" className="text-label text-success">Đã lưu hồ sơ.</p>}
      <div className="flex flex-wrap gap-2 border-t border-border pt-4">
        <Button type="submit" loading={saving} disabled={!account || saving}>
          {profile ? 'Lưu thay đổi' : 'Lưu và tiếp tục'}
        </Button>
        {!profile && (
          <Button type="button" variant="ghost" loading={leaving} disabled={saving} onClick={logout}>
            Đăng xuất
          </Button>
        )}
      </div>
    </form>
  );
}

function ProfileSelect({ label, value, onChange, children }: {
  label: string; value: string; onChange: (value: string) => void; children: ReactNode;
}) {
  return (
    <FormField label={label} required>
      {(field) => (
        <select {...field} required className={selectClass} value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="" disabled>Chọn một mục</option>
          {children}
        </select>
      )}
    </FormField>
  );
}
