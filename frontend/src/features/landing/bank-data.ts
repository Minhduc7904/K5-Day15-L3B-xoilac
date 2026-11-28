/**
 * Số liệu ngân hàng câu hỏi mẫu của bản chạy thử, đếm từ data/question_bank.csv (1.279 câu, tất cả đã duyệt)
 * và data/chapters.csv. Là số liệu tĩnh nên khi nạp lại ngân hàng cần cập nhật file này.
 * Tên chương rút gọn từ tên đầy đủ trong data/chapters.csv.
 */

export type Grade = 10 | 11 | 12;

export interface BankChapter {
  code: string;
  grade: Grade;
  name: string;
  count: number;
}

export const bankChapters: BankChapter[] = [
  { code: '10C1', grade: 10, name: 'Mệnh đề và tập hợp', count: 59 },
  { code: '10C2', grade: 10, name: 'Bất phương trình bậc nhất hai ẩn', count: 23 },
  { code: '10C3', grade: 10, name: 'Hệ thức lượng trong tam giác', count: 40 },
  { code: '10C4', grade: 10, name: 'Vectơ', count: 51 },
  { code: '10C5', grade: 10, name: 'Số đặc trưng mẫu số liệu', count: 11 },
  { code: '10C6', grade: 10, name: 'Hàm số, đồ thị và ứng dụng', count: 15 },
  { code: '10C7', grade: 10, name: 'Toạ độ trong mặt phẳng', count: 45 },
  { code: '10C8', grade: 10, name: 'Đại số tổ hợp', count: 32 },
  { code: '10C9', grade: 10, name: 'Xác suất cổ điển', count: 17 },
  { code: '11C1', grade: 11, name: 'Lượng giác', count: 145 },
  { code: '11C2', grade: 11, name: 'Dãy số, cấp số cộng, cấp số nhân', count: 75 },
  { code: '11C3', grade: 11, name: 'Số đặc trưng xu thế trung tâm', count: 15 },
  { code: '11C4', grade: 11, name: 'Quan hệ song song trong không gian', count: 39 },
  { code: '11C5', grade: 11, name: 'Giới hạn, hàm số liên tục', count: 41 },
  { code: '11C6', grade: 11, name: 'Hàm số mũ và lôgarit', count: 65 },
  { code: '11C7', grade: 11, name: 'Quan hệ vuông góc trong không gian', count: 40 },
  { code: '11C8', grade: 11, name: 'Quy tắc tính xác suất', count: 35 },
  { code: '11C9', grade: 11, name: 'Đạo hàm', count: 29 },
  { code: '12C1', grade: 12, name: 'Ứng dụng đạo hàm', count: 177 },
  { code: '12C2', grade: 12, name: 'Vectơ trong không gian', count: 83 },
  { code: '12C3', grade: 12, name: 'Mẫu số liệu ghép nhóm', count: 16 },
  { code: '12C4', grade: 12, name: 'Nguyên hàm và tích phân', count: 124 },
  { code: '12C5', grade: 12, name: 'Toạ độ trong không gian', count: 69 },
  { code: '12C6', grade: 12, name: 'Xác suất có điều kiện', count: 32 },
];

export const bankTotals = {
  questions: 1279,
  chapters: bankChapters.length,
  subtopics: 76,
} as const;

export const gradeTotals: Record<Grade, number> = bankChapters.reduce(
  (acc, c) => ({ ...acc, [c.grade]: acc[c.grade] + c.count }),
  { 10: 0, 11: 0, 12: 0 } as Record<Grade, number>,
);

/** Màu theo thang lạnh → nóng: câu càng khó càng nóng. Chữ NB/TH/VD/VDC luôn đi kèm màu. */
export const bankDifficulty = [
  { code: 'NB', name: 'Nhận biết', count: 304, color: '#9be3f2' },
  { code: 'TH', name: 'Thông hiểu', count: 333, color: '#4fc6e0' },
  { code: 'VD', name: 'Vận dụng', count: 538, color: '#00a0c8' },
  { code: 'VDC', name: 'Vận dụng cao', count: 104, color: '#f97316' },
] as const;

export const bankTypes = [
  { code: 'SINGLE_CHOICE', name: 'Trắc nghiệm', count: 752, color: '#00a0c8' },
  { code: 'SHORT_ANSWER', name: 'Trả lời ngắn', count: 308, color: '#fbbf24' },
  { code: 'TRUE_FALSE', name: 'Đúng/sai', count: 219, color: '#e8f0fa' },
] as const;
