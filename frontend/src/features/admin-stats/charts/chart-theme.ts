/**
 * Màu và định dạng dùng chung cho các chart ở dashboard admin.
 * Ba màu phân loại đầu (xanh dương, cam, xanh ngọc) lấy từ bảng màu đã qua validate_palette (CVD ΔE ≥ 8, nền sáng);
 * xanh ngọc dưới 3:1 trên nền trắng nên mọi chart có chú giải và nút "Bảng" để xem số liệu.
 * Màu navy thương hiệu không dùng làm màu phân loại vì ngoài dải sáng cho phép.
 */
export const CHART = {
  s1: '#2a78d6',
  s2: '#eb6834',
  s3: '#1baf7a',
  grid: '#e1e0d9',
  axis: '#898781',
  surface: '#ffffff',
} as const;

/** Thang tuần tự một tông xanh, bước 100 → 700, cho heatmap (ô nhạt nhất ≈ "gần 0"). */
export const SEQUENTIAL = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'] as const;

/** Thang thứ tự cho các bước phễu: bước nhạt nhất vẫn ≥ 2:1 so với nền. */
export const ORDINAL = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'] as const;

export const tickStyle = { fill: CHART.axis, fontSize: 11 } as const;

const numberFormat = new Intl.NumberFormat('vi-VN');
export const fmtInt = (n: number) => numberFormat.format(n);
export const fmtPct = (ratio: number) => `${numberFormat.format(Math.round(ratio * 100))}%`;
export const fmtScore = (n: number) => numberFormat.format(Math.round(n * 10) / 10);

/** 2026-11-28 → 28/11 */
export function shortDay(iso: string): string {
  const [, month, day] = iso.split('-');
  return `${Number(day)}/${Number(month)}`;
}

export const WEEKDAYS = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật'] as const;

/** Chọn chữ trắng hay chữ tối cho nền thuộc thang SEQUENTIAL theo bậc. */
export const onSequential = (step: number) => (step >= 3 ? '#ffffff' : '#03172f');

/** Bậc 0..6 của thang tuần tự theo tỉ lệ so với giá trị lớn nhất; giá trị 0 trả -1 (ô trống). */
export function sequentialStep(value: number, max: number): number {
  if (value <= 0 || max <= 0) return -1;
  return Math.min(SEQUENTIAL.length - 1, Math.floor((value / max) * SEQUENTIAL.length));
}
