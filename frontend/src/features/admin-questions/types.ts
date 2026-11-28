/** Kiểu dữ liệu API ngân hàng câu hỏi cho admin (#11). Khớp backend/app/schemas/admin_bank.py. */

export type QuestionType = 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'TRUE_FALSE' | 'SHORT_ANSWER' | 'ESSAY';
export type Difficulty = 'NB' | 'TH' | 'VD' | 'VDC';
export type Visibility = 'DRAFT' | 'PRIVATE' | 'PUBLISHED';
export type QuestionStatus = Visibility | 'ARCHIVED';

export const QUESTION_TYPES: Record<QuestionType, string> = {
  SINGLE_CHOICE: 'Trắc nghiệm một đáp án',
  MULTIPLE_CHOICE: 'Trắc nghiệm nhiều đáp án',
  TRUE_FALSE: 'Đúng/sai',
  SHORT_ANSWER: 'Trả lời ngắn',
  ESSAY: 'Tự luận',
};
export const DIFFICULTIES: Record<Difficulty, string> = { NB: 'Nhận biết', TH: 'Thông hiểu', VD: 'Vận dụng', VDC: 'Vận dụng cao' };
export const STATUSES: Record<QuestionStatus, string> = {
  PUBLISHED: 'Đã duyệt',
  DRAFT: 'Nháp',
  PRIVATE: 'Riêng tư',
  ARCHIVED: 'Ngừng sử dụng',
};
export const GRADES = [10, 11, 12] as const;

export interface ChapterRef {
  chapter_id: number;
  code: string | null;
  name: string;
}

export interface QuestionSummary {
  question_id: number;
  code: string;
  content: string;
  type: QuestionType;
  difficulty: Difficulty | null;
  grade: number | null;
  visibility: Visibility;
  status: QuestionStatus;
  archived_at: string | null;
  updated_at: string | null;
  chapters: ChapterRef[];
}

export interface Statement {
  statement_id: number;
  content: string;
  is_correct: boolean;
  order: number | null;
}

export interface QuestionDetail extends QuestionSummary {
  correct_answer: string | null;
  solution: string | null;
  statements: Statement[];
  media_ids: number[];
  exam_count: number;
  created_at: string | null;
}

export interface QuestionList {
  items: QuestionSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuestionQuery {
  q?: string;
  grade?: number;
  chapter_id?: number;
  type?: QuestionType;
  difficulty?: Difficulty;
  status?: QuestionStatus;
  page: number;
  page_size: number;
}

export interface StatementInput {
  statement_id?: number | null;
  content: string;
  is_correct: boolean;
}

export interface QuestionInput {
  content: string;
  type: QuestionType;
  difficulty: Difficulty | null;
  grade: number | null;
  visibility: Visibility;
  correct_answer: string | null;
  solution: string | null;
  statements: StatementInput[];
  chapter_ids: number[];
}
