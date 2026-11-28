/**
 * Bản sao luật kiểm câu theo loại của backend (`validate_question` ở backend/app/usecase/admin_questions.py),
 * chỉ để báo lỗi sớm trên form. Backend vẫn là nơi quyết định; lỗi từ API được hiện nguyên văn.
 */
import type { QuestionInput } from './types';

const CHOICE = new Set(['SINGLE_CHOICE', 'MULTIPLE_CHOICE']);

export function validateQuestion(input: QuestionInput): string | null {
  if (!input.content.trim()) return 'Nội dung câu hỏi không được để trống';
  const options = input.statements;
  if (options.some((s) => !s.content.trim())) return 'Lựa chọn/mệnh đề không được để trống';
  const correct = options.filter((s) => s.is_correct).length;
  if (CHOICE.has(input.type) && options.length < 2) return 'Câu trắc nghiệm cần ít nhất 2 lựa chọn';
  if (input.type === 'SINGLE_CHOICE' && correct !== 1) return 'Câu một đáp án cần đúng 1 lựa chọn đúng';
  if (input.type === 'MULTIPLE_CHOICE' && correct < 1) return 'Câu nhiều đáp án cần ít nhất 1 lựa chọn đúng';
  if (input.type === 'TRUE_FALSE' && options.length === 0) return 'Câu đúng/sai cần ít nhất 1 mệnh đề';
  if (input.type === 'SHORT_ANSWER' && !input.correct_answer?.trim()) return 'Câu trả lời ngắn cần đáp án';
  if ((input.type === 'SHORT_ANSWER' || input.type === 'ESSAY') && options.length) return 'Câu trả lời ngắn và tự luận không có lựa chọn';
  if (input.chapter_ids.length === 0) return 'Chọn ít nhất một chương';
  if (input.chapter_ids.length > 10) return 'Tối đa 10 chương';
  if (options.length > 12) return 'Tối đa 12 lựa chọn';
  return null;
}

export const usesStatements = (type: QuestionInput['type']) => CHOICE.has(type) || type === 'TRUE_FALSE';
