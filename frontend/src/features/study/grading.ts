import type { Answer, Exam, Question } from './types';

/**
 * Chấm điểm luyện tập bằng code, so với đáp án trong ngân hàng (spec §4, hướng mở rộng).
 * Điểm theo cách tính của đề THPT từ 2025, rồi quy về thang 10 theo số câu của đề:
 * - Trắc nghiệm: 0,25 điểm/câu.
 * - Đúng/Sai (4 ý): đúng 1 ý 0,1 · 2 ý 0,25 · 3 ý 0,5 · 4 ý 1 điểm.
 * - Trả lời ngắn: 0,5 điểm/câu.
 */
const TF_POINTS = [0, 0.1, 0.25, 0.5, 1];

export const maxPoints = (q: Question) => (q.type === 'SINGLE_CHOICE' ? 0.25 : q.type === 'TRUE_FALSE' ? 1 : 0.5);

/** So khớp trả lời ngắn: bỏ khoảng trắng, chấp nhận cả dấu phẩy và dấu chấm thập phân. */
export const normalizeShort = (value: string) => value.trim().replace(/\s+/g, '').replace('.', ',');

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

export function gradeQuestion(question: Question, answer: Answer): QuestionResult {
  const max = maxPoints(question);
  if (!hasAnswer(answer)) return { question, answer: null, points: 0, max, status: 'skipped' };

  if (question.type === 'SINGLE_CHOICE') {
    const ok = question.statements.find((s) => s.correct)?.label === answer;
    return { question, answer, points: ok ? max : 0, max, status: ok ? 'correct' : 'wrong' };
  }
  if (question.type === 'SHORT_ANSWER') {
    const ok = typeof answer === 'string' && normalizeShort(answer) === normalizeShort(question.answer ?? '');
    return { question, answer, points: ok ? max : 0, max, status: ok ? 'correct' : 'wrong' };
  }
  const picks = Array.isArray(answer) ? answer : [];
  const tfCorrect = question.statements.filter((s, i) => picks[i] === s.correct).length;
  const points = TF_POINTS[tfCorrect] ?? 0;
  return {
    question,
    answer,
    points,
    max,
    tfCorrect,
    status: tfCorrect === question.statements.length ? 'correct' : tfCorrect === 0 ? 'wrong' : 'partial',
  };
}

export function gradeExam(exam: Exam, questionsById: Map<string, Question>, answers: Record<string, Answer>) {
  const results = exam.sections.flatMap((section) =>
    section.questionIds.map((id) => {
      const question = questionsById.get(id);
      if (!question) throw new Error(`Thiếu câu ${id}`);
      return gradeQuestion(question, answers[id] ?? null);
    }),
  );
  const raw = results.reduce((sum, r) => sum + r.points, 0);
  const max = results.reduce((sum, r) => sum + r.max, 0);
  const score = max ? Math.round((raw / max) * 10 * 100) / 100 : 0;
  return {
    results,
    score,
    correct: results.filter((r) => r.status === 'correct').length,
    total: results.length,
  };
}

/** Đáp án đúng của một câu, ở dạng `Answer`, để dựng dữ liệu mẫu. */
export function correctAnswer(question: Question): Answer {
  if (question.type === 'SINGLE_CHOICE') return question.statements.find((s) => s.correct)?.label ?? null;
  if (question.type === 'SHORT_ANSWER') return question.answer ?? null;
  return question.statements.map((s) => s.correct);
}

/** Một trả lời sai cố định, để dữ liệu mẫu có câu sai. */
export function wrongAnswer(question: Question): Answer {
  if (question.type === 'SINGLE_CHOICE') return question.statements.find((s) => !s.correct)?.label ?? null;
  if (question.type === 'SHORT_ANSWER') return '2';
  // Sai 2 ý đầu: vẫn được điểm một phần.
  return question.statements.map((s, i) => (i < 2 ? !s.correct : s.correct));
}

export const formatScore = (score: number) => score.toLocaleString('vi-VN', { maximumFractionDigits: 2 });
