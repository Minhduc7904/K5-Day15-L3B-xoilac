import type { Chapter } from '../types';
import { subchapters } from './subchapters';

/** Chương cấp 0 lấy từ `data/chapters.csv` (tên viết lại theo kiểu câu cho dễ đọc). */
export const chapters: Chapter[] = [
  { code: '10C1', name: 'Mệnh đề và tập hợp', grade: 10 },
  { code: '10C2', name: 'Bất phương trình bậc nhất hai ẩn', grade: 10 },
  { code: '10C3', name: 'Hệ thức lượng trong tam giác', grade: 10 },
  { code: '10C4', name: 'Vectơ', grade: 10 },
  { code: '10C5', name: 'Số đặc trưng của mẫu số liệu không ghép nhóm', grade: 10 },
  { code: '10C7', name: 'Phương pháp toạ độ trong mặt phẳng', grade: 10 },
  { code: '10C8', name: 'Đại số tổ hợp', grade: 10 },
  { code: '10C9', name: 'Xác suất theo định nghĩa cổ điển', grade: 10 },
  { code: '11C1', name: 'Hàm số lượng giác và phương trình lượng giác', grade: 11 },
  { code: '11C2', name: 'Dãy số, cấp số cộng, cấp số nhân', grade: 11 },
  { code: '11C3', name: 'Số đặc trưng đo xu thế trung tâm (ghép nhóm)', grade: 11 },
  { code: '11C4', name: 'Quan hệ song song trong không gian', grade: 11 },
  { code: '11C5', name: 'Giới hạn, hàm số liên tục', grade: 11 },
  { code: '11C6', name: 'Hàm số mũ và hàm số lôgarit', grade: 11 },
  { code: '11C7', name: 'Quan hệ vuông góc trong không gian', grade: 11 },
  { code: '11C8', name: 'Các quy tắc tính xác suất', grade: 11 },
  { code: '11C9', name: 'Đạo hàm', grade: 11 },
  { code: '12C1', name: 'Ứng dụng đạo hàm để khảo sát hàm số', grade: 12 },
  { code: '12C2', name: 'Vectơ và hệ trục toạ độ trong không gian', grade: 12 },
  { code: '12C3', name: 'Số đặc trưng đo mức độ phân tán (ghép nhóm)', grade: 12 },
  { code: '12C4', name: 'Nguyên hàm và tích phân', grade: 12 },
  { code: '12C5', name: 'Phương pháp toạ độ trong không gian', grade: 12 },
  { code: '12C6', name: 'Xác suất có điều kiện', grade: 12 },
];

const byCode = new Map<string, Chapter>([...subchapters, ...chapters].map((c) => [c.code, c]));

export const chapterOf = (code: string): Chapter => byCode.get(code) ?? { code, name: code, grade: 12 };

export const difficultyLabels = { NB: 'Nhận biết', TH: 'Thông hiểu', VD: 'Vận dụng', VDC: 'Vận dụng cao' } as const;

export const typeLabels = {
  SINGLE_CHOICE: 'Trắc nghiệm',
  TRUE_FALSE: 'Đúng / Sai',
  SHORT_ANSWER: 'Trả lời ngắn',
  MULTIPLE_CHOICE: 'Nhiều đáp án',
  ESSAY: 'Tự luận',
} as const;
