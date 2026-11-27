const DAY = 24 * 60 * 60 * 1000;

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

/** "Hôm nay", "Hôm qua", "3 ngày trước", rồi tới ngày cụ thể. */
export function relativeDay(iso: string) {
  const diff = Math.round((startOfDay(new Date()) - startOfDay(new Date(iso))) / DAY);
  if (diff <= 0) return 'Hôm nay';
  if (diff === 1) return 'Hôm qua';
  if (diff < 7) return `${diff} ngày trước`;
  return new Date(iso).toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' });
}

export const shortDate = (iso: string) => new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });

export const longDate = (iso: string) =>
  new Date(iso).toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'numeric', year: 'numeric' });

/** Thời lượng đề. `0` nghĩa là không giới hạn thời gian. */
export const examDuration = (minutes: number) => (minutes > 0 ? `${minutes} phút` : 'Không giới hạn');

export function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m >= 60) return `${Math.floor(m / 60)} giờ ${m % 60} phút`;
  if (m === 0) return `${s} giây`;
  return s ? `${m} phút ${s} giây` : `${m} phút`;
}

/** Đồng hồ đếm ngược mm:ss. */
export const clock = (seconds: number) => {
  const safe = Math.max(0, seconds);
  return `${String(Math.floor(safe / 60)).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`;
};

export type ScoreTone = 'success' | 'primary' | 'warning' | 'danger';

export const scoreTone = (score: number): ScoreTone =>
  score >= 8 ? 'success' : score >= 6.5 ? 'primary' : score >= 5 ? 'warning' : 'danger';

export const accuracyTone = (ratio: number): Exclude<ScoreTone, 'primary'> =>
  ratio >= 0.75 ? 'success' : ratio >= 0.5 ? 'warning' : 'danger';

export const percent = (ratio: number) => `${Math.round(ratio * 100)}%`;
