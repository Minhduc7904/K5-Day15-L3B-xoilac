/**
 * Kiểu dữ liệu của phần học sinh: câu hỏi, đề, lượt làm bài, thống kê.
 * Bám cấu trúc bảng nội dung ở production (`questions`, `statements`, `exams`, `sections`,
 * `questions_exams`, `media`): nội dung là văn bản có LaTeX `$…$`/`$$…$$` và ảnh `![media:ID](media:ID)`.
 */

export type Difficulty = 'NB' | 'TH' | 'VD' | 'VDC';
export type QuestionType = 'SINGLE_CHOICE' | 'TRUE_FALSE' | 'SHORT_ANSWER';

export interface Chapter {
  code: string;
  name: string;
  grade: 10 | 11 | 12;
}

/** Một lựa chọn (trắc nghiệm) hoặc một ý (đúng/sai). Khớp bảng `statements`. */
export interface Statement {
  label: string;
  content: string;
  correct: boolean;
}

export interface Question {
  id: string;
  type: QuestionType;
  difficulty: Difficulty;
  chapter: string;
  content: string;
  statements: Statement[];
  /** Đáp án của câu trả lời ngắn (vd `0,58`). */
  answer?: string;
  solution?: string;
}

/** Câu hỏi khi đang làm bài: không có đáp án, không có lời giải. */
export type PublicQuestion = Omit<Question, 'answer' | 'solution' | 'statements'> & {
  statements: Array<Omit<Statement, 'correct'>>;
};

export interface ExamSection {
  id: string;
  title: string;
  type: QuestionType;
  questionIds: string[];
}

export type ExamSource = 'ai' | 'bank';

export interface Exam {
  id: string;
  title: string;
  source: ExamSource;
  /** Lời nhắn đã dùng để tạo đề với agent (nếu có). */
  prompt?: string;
  reason?: string;
  createdAt: string;
  durationMinutes: number;
  chapters: string[];
  sections: ExamSection[];
}

/** Trả lời của một câu: chữ cái (trắc nghiệm), mảng Đ/S theo ý (đúng/sai), chuỗi (trả lời ngắn). */
export type Answer = string | Array<boolean | null> | null;

export interface Attempt {
  id: string;
  examId: string;
  startedAt: string;
  submittedAt: string;
  durationSeconds: number;
  answers: Record<string, Answer>;
  /**
   * Số giây học sinh để mở từng câu (cộng dồn cả các lần quay lại). Lượt cũ trước khi có tính năng này không có trường này.
   */
  questionSeconds?: Record<string, number>;
  /** Điểm luyện tập trên thang 10, do code chấm so với đáp án trong ngân hàng. Không phải điểm chính thức. */
  score: number;
  correct: number;
  total: number;
}

export interface ExamSummary extends Exam {
  questionCount: number;
  attempts: number;
  bestScore: number | null;
  lastAttemptAt: string | null;
}

export interface ChapterStat {
  chapter: Chapter;
  correct: number;
  total: number;
}

export interface DashboardData {
  streak: { current: number; best: number; days: Array<{ date: string; studied: boolean }> };
  totals: { exams: number; questions: number; minutes: number; average: number | null };
  scores: Array<{ attemptId: string; examId: string; title: string; date: string; score: number }>;
  chapters: ChapterStat[];
  recent: Array<{ attempt: Attempt; exam: Exam }>;
}

/** Cấu trúc đề agent đề xuất ở bước xem trước, học sinh chỉnh trước khi dựng đề. */
export interface StructureRow {
  chapter: string;
  difficulty: Difficulty;
  type: QuestionType;
  count: number;
}

export interface StructureProposal {
  title: string;
  reason: string;
  durationMinutes: number;
  rows: StructureRow[];
}
