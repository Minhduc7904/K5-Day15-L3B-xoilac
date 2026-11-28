import type { Answer, Question } from './types';

/**
 * Kiểu và hàm dùng chung cho kết quả làm bài. Việc chấm điểm do backend thực hiện (xem `attempt-api.ts`),
 * frontend chỉ hiển thị điểm và trạng thái từng câu mà server trả về.
 */

export function hasAnswer(answer: Answer | undefined): boolean {
  if (typeof answer === 'string') return answer.trim() !== '';
  return Array.isArray(answer) && answer.some((value) => value !== null);
}

export interface QuestionResult {
  question: Question;
  answer: Answer;
  points: number;
  max: number;
  status: 'correct' | 'partial' | 'wrong' | 'skipped';
  /** Số ý đúng của câu Đúng/Sai. */
  tfCorrect?: number;
}

export const formatScore = (score: number) => score.toLocaleString('vi-VN', { maximumFractionDigits: 2 });
