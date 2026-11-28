import type { Difficulty, QuestionType } from './types';

/** Ba dạng câu chấm tự động được, theo thứ tự các phần của đề THPT. */
export const TYPES: QuestionType[] = ['SINGLE_CHOICE', 'TRUE_FALSE', 'SHORT_ANSWER'];
export const DIFFS: Difficulty[] = ['NB', 'TH', 'VD', 'VDC'];

export const difficultyLabels = { NB: 'Nhận biết', TH: 'Thông hiểu', VD: 'Vận dụng', VDC: 'Vận dụng cao' } as const;

export const typeLabels = {
  SINGLE_CHOICE: 'Trắc nghiệm',
  TRUE_FALSE: 'Đúng / Sai',
  SHORT_ANSWER: 'Trả lời ngắn',
  MULTIPLE_CHOICE: 'Nhiều đáp án',
  ESSAY: 'Tự luận',
} as const;

export const typeColor: Record<QuestionType, string> = {
  SINGLE_CHOICE: 'bg-primary',
  TRUE_FALSE: 'bg-accent',
  SHORT_ANSWER: 'bg-ember',
  MULTIPLE_CHOICE: 'bg-info',
  ESSAY: 'bg-warning',
};

export const diffColor: Record<Difficulty, string> = {
  NB: 'bg-success',
  TH: 'bg-info',
  VD: 'bg-warning',
  VDC: 'bg-danger',
};
