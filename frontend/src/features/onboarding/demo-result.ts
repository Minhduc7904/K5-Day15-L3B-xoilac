/**
 * Kết quả minh hoạ cho chặng "Kết quả" của tour hướng dẫn.
 *
 * Chỉ dùng khi học sinh chưa có lượt làm nào: tour mở `/results/demo` thay cho một lượt thật. Nội dung do nhóm tự viết
 * (chữ và công thức, không có ảnh), không lấy từ ngân hàng câu hỏi, không ghi vào cơ sở dữ liệu và không tính vào
 * tổng quan hay chuỗi ngày học. Trang kết quả luôn hiện biểu ngữ nói rõ đây không phải bài của học sinh.
 */
import { registerChapter } from '../study/chapters';
import type { QuestionResult } from '../study/grading';
import type { Attempt, Exam, Question } from '../study/types';

export const DEMO_RESULT_ID = 'demo';

const CHAPTERS = {
  function: 'DEMO-HAM-SO',
  probability: 'DEMO-XAC-SUAT',
} as const;

const abcd = (a: string, b: string, c: string, d: string, correct: number) =>
  [a, b, c, d].map((content, index) => ({ label: 'ABCD'[index], content, correct: index === correct }));

const tf = (items: Array<[string, boolean]>) =>
  items.map(([content, correct], index) => ({ label: 'abcd'[index], content, correct }));

const QUESTIONS: Question[] = [
  {
    id: 'demo-1', type: 'SINGLE_CHOICE', difficulty: 'NB', chapter: CHAPTERS.function,
    content: 'Đạo hàm của hàm số $y = x^3 - 3x + 1$ là:',
    statements: abcd('$y\' = 3x^2 - 3$', '$y\' = 3x^2 + 3$', '$y\' = x^2 - 3$', '$y\' = 3x - 3$', 0),
    solution: 'Áp dụng $(x^n)\' = n x^{n-1}$ cho từng số hạng: $(x^3)\' = 3x^2$, $(3x)\' = 3$, hằng số có đạo hàm $0$. Vậy $y\' = 3x^2 - 3$.',
  },
  {
    id: 'demo-2', type: 'SINGLE_CHOICE', difficulty: 'TH', chapter: CHAPTERS.function,
    content: 'Tập xác định của hàm số $y = \\sqrt{x - 2}$ là:',
    statements: abcd('$\\mathbb{R}$', '$(2; +\\infty)$', '$[2; +\\infty)$', '$(-\\infty; 2]$', 2),
    solution: 'Căn thức xác định khi biểu thức trong căn không âm: $x - 2 \\ge 0 \\iff x \\ge 2$. Vậy tập xác định là $[2; +\\infty)$, nhớ lấy cả đầu mút $2$.',
  },
  {
    id: 'demo-3', type: 'TRUE_FALSE', difficulty: 'TH', chapter: CHAPTERS.function,
    content: 'Cho hàm số $f(x) = x^2 - 4x + 3$. Xét tính đúng sai của các mệnh đề sau:',
    statements: tf([
      ['Đồ thị của $f(x)$ là parabol có bề lõm hướng lên trên.', true],
      ['$f(x)$ đạt giá trị nhỏ nhất bằng $-1$ tại $x = 2$.', true],
      ['Phương trình $f(x) = 0$ có hai nghiệm trái dấu.', false],
      ['$f(x) > 0$ với mọi số thực $x$.', false],
    ]),
    solution: 'Hệ số $a = 1 > 0$ nên bề lõm hướng lên. Đỉnh $(2; -1)$ nên giá trị nhỏ nhất là $-1$. Phương trình $f(x) = 0$ có hai nghiệm $x = 1$ và $x = 3$ cùng dương, không trái dấu. Vì $f(2) = -1 < 0$ nên mệnh đề cuối sai.',
  },
  {
    id: 'demo-4', type: 'TRUE_FALSE', difficulty: 'VD', chapter: CHAPTERS.probability,
    content: 'Một hộp có $5$ bi đỏ và $3$ bi xanh. Lấy ngẫu nhiên đồng thời $2$ bi. Xét các mệnh đề sau:',
    statements: tf([
      ['Số cách lấy $2$ bi bất kì là $28$.', true],
      ['Xác suất lấy được $2$ bi đỏ là $\\dfrac{10}{28}$.', true],
      ['Xác suất lấy được $2$ bi cùng màu là $\\dfrac{13}{28}$.', true],
      ['Xác suất lấy được ít nhất một bi xanh là $\\dfrac{9}{28}$.', false],
    ]),
    solution: 'Số cách lấy $2$ bi là $C_8^2 = 28$. Hai bi đỏ có $C_5^2 = 10$ cách; hai bi xanh có $C_3^2 = 3$ cách, nên cùng màu có $13$ cách. Ít nhất một bi xanh là biến cố đối của hai bi đỏ: $1 - \\dfrac{10}{28} = \\dfrac{18}{28}$, không phải $\\dfrac{9}{28}$.',
  },
  {
    id: 'demo-5', type: 'SHORT_ANSWER', difficulty: 'TH', chapter: CHAPTERS.function,
    content: 'Giá trị nhỏ nhất của hàm số $y = x^2 - 4x + 7$ bằng bao nhiêu?',
    statements: [], answer: '3',
    solution: 'Viết $y = (x - 2)^2 + 3 \\ge 3$, dấu bằng xảy ra khi $x = 2$. Vậy giá trị nhỏ nhất là $3$.',
  },
  {
    id: 'demo-6', type: 'SHORT_ANSWER', difficulty: 'VD', chapter: CHAPTERS.function,
    content: 'Tính $\\displaystyle\\lim_{x \\to 2} \\dfrac{x^2 - 4}{x - 2}$.',
    statements: [], answer: '4',
    solution: 'Phân tích $x^2 - 4 = (x - 2)(x + 2)$ rồi rút gọn $(x - 2)$, được $\\lim_{x \\to 2} (x + 2) = 4$.',
  },
];

/** Đáp án học sinh giả định, điểm từng câu và số giây mở câu. */
const SCRIPT: Array<{ answer: QuestionResult['answer']; points: number; max: number; status: QuestionResult['status']; seconds: number; tfCorrect?: number }> = [
  { answer: 'A', points: 0.25, max: 0.25, status: 'correct', seconds: 48 },
  { answer: 'B', points: 0, max: 0.25, status: 'wrong', seconds: 95 },
  { answer: [true, true, true, false], points: 0.5, max: 1, status: 'partial', seconds: 140, tfCorrect: 3 },
  { answer: [true, true, true, false], points: 1, max: 1, status: 'correct', seconds: 210, tfCorrect: 4 },
  { answer: '3', points: 0.5, max: 0.5, status: 'correct', seconds: 120 },
  { answer: null, points: 0, max: 0.5, status: 'skipped', seconds: 30 },
];

/** Dựng bộ kết quả theo đúng hình dạng mà `attemptApi.result` trả về. */
export function demoResult() {
  registerChapter(CHAPTERS.function, 'Hàm số và đồ thị (minh hoạ)', 12);
  registerChapter(CHAPTERS.probability, 'Xác suất (minh hoạ)', 12);

  const exam: Exam = {
    id: DEMO_RESULT_ID,
    title: 'Đề minh hoạ: Hàm số và xác suất',
    source: 'ai',
    createdAt: new Date().toISOString(),
    durationMinutes: 15,
    chapters: [CHAPTERS.function, CHAPTERS.probability],
    sections: [
      { id: 'demo-s1', title: 'Phần 1: Trắc nghiệm', type: 'SINGLE_CHOICE', questionIds: ['demo-1', 'demo-2'] },
      { id: 'demo-s2', title: 'Phần 2: Đúng/Sai', type: 'TRUE_FALSE', questionIds: ['demo-3', 'demo-4'] },
      { id: 'demo-s3', title: 'Phần 3: Trả lời ngắn', type: 'SHORT_ANSWER', questionIds: ['demo-5', 'demo-6'] },
    ],
  };

  const results: QuestionResult[] = QUESTIONS.map((question, index) => {
    const row = SCRIPT[index];
    return { question, answer: row.answer, points: row.points, max: row.max, status: row.status, tfCorrect: row.tfCorrect };
  });
  const totalPoints = SCRIPT.reduce((sum, row) => sum + row.points, 0);
  const totalMax = SCRIPT.reduce((sum, row) => sum + row.max, 0);
  const score = Math.round((totalPoints / totalMax) * 1000) / 100;
  const correct = results.filter((result) => result.status === 'correct').length;

  const duration = SCRIPT.reduce((sum, row) => sum + row.seconds, 0);
  const submitted = new Date();
  const attempt: Attempt = {
    id: DEMO_RESULT_ID,
    examId: exam.id,
    startedAt: new Date(submitted.getTime() - duration * 1000).toISOString(),
    submittedAt: submitted.toISOString(),
    reason: 'manual',
    durationSeconds: duration,
    answers: Object.fromEntries(results.map((result) => [result.question.id, result.answer])),
    questionSeconds: Object.fromEntries(QUESTIONS.map((question, index) => [question.id, SCRIPT[index].seconds])),
    score, correct, total: QUESTIONS.length, answered: results.filter((result) => result.status !== 'skipped').length,
  };

  return { attempt, exam, graded: { results, score, correct, total: QUESTIONS.length }, previous: undefined as Attempt | undefined };
}
