import { correctAnswer, gradeExam, wrongAnswer } from '../grading';
import type { Answer, Attempt, Exam } from '../types';
import { questions } from './questions';

/**
 * Dữ liệu mẫu (synthetic) cho phần học sinh ở chế độ mock. Ngày tháng tính lùi từ hôm nay để
 * chuỗi ngày học và biểu đồ luôn trông "đang dùng". Điểm được chấm lại bằng `gradeExam`, không gõ tay.
 */

const DAY = 24 * 60 * 60 * 1000;

export const daysAgo = (n: number, hour = 20, minute = 0) => {
  const d = new Date(Date.now() - n * DAY);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString();
};

export const seedExams = (): Exam[] => [
  {
    id: 'de-ung-dung-dao-ham',
    title: 'Ôn chương yếu: Ứng dụng đạo hàm & tích phân',
    source: 'ai',
    prompt: 'Mình hay sai phần khảo sát hàm số, ra giúp mình đề 30 phút nhé',
    reason: 'Chương Ứng dụng đạo hàm có tỉ lệ đúng thấp nhất trong 3 lượt gần đây, nên đề dồn nhiều câu vào chương này, thêm một phần tích phân để ôn liền mạch.',
    createdAt: daysAgo(18, 19, 30),
    durationMinutes: 30,
    chapters: ['12C1', '12C4'],
    sections: [
      { id: 'p1', title: 'Phần 1: Trắc nghiệm', type: 'SINGLE_CHOICE', questionIds: ['q01', 'q02', 'q03', 'q04', 'q05', 'q06'] },
      { id: 'p2', title: 'Phần 2: Đúng sai', type: 'TRUE_FALSE', questionIds: ['t01', 't02'] },
      { id: 'p3', title: 'Phần 3: Trả lời ngắn', type: 'SHORT_ANSWER', questionIds: ['s01', 's02'] },
    ],
  },
  {
    id: 'de-tong-hop-thpt',
    title: 'Đề tổng hợp theo cấu trúc THPT (rút gọn)',
    source: 'bank',
    createdAt: daysAgo(27, 9),
    durationMinutes: 60,
    chapters: ['12C1', '12C4', '11C6', '11C7', '12C5', '12C3', '11C9', '10C9'],
    sections: [
      { id: 'p1', title: 'Phần 1: Trắc nghiệm', type: 'SINGLE_CHOICE', questionIds: ['q01', 'q02', 'q03', 'q04', 'q05', 'q06', 'q07', 'q08', 'q09', 'q10', 'q11', 'q12'] },
      { id: 'p2', title: 'Phần 2: Đúng sai', type: 'TRUE_FALSE', questionIds: ['t01', 't02', 't03'] },
      { id: 'p3', title: 'Phần 3: Trả lời ngắn', type: 'SHORT_ANSWER', questionIds: ['s01', 's02', 's03', 's04'] },
    ],
  },
  {
    id: 'de-mu-logarit-khong-gian',
    title: 'Mũ – lôgarit và hình học không gian',
    source: 'ai',
    prompt: 'Cho mình đề ngắn kết hợp mũ logarit với hình không gian',
    reason: 'Bạn chọn hai chương này. Đề giữ ở mức Nhận biết – Thông hiểu vì đây là lần đầu bạn ôn hai chương cùng lúc.',
    createdAt: daysAgo(23, 21),
    durationMinutes: 25,
    chapters: ['11C6', '11C7', '12C5', '12C3', '11C9', '10C9'],
    sections: [
      { id: 'p1', title: 'Phần 1: Trắc nghiệm', type: 'SINGLE_CHOICE', questionIds: ['q07', 'q08', 'q09', 'q10', 'q11', 'q12'] },
      { id: 'p2', title: 'Phần 2: Đúng sai', type: 'TRUE_FALSE', questionIds: ['t03'] },
      { id: 'p3', title: 'Phần 3: Trả lời ngắn', type: 'SHORT_ANSWER', questionIds: ['s03', 's04'] },
    ],
  },
  {
    id: 'de-tich-phan-cap-toc',
    title: 'Tích phân cấp tốc 15 phút',
    source: 'ai',
    prompt: 'Đề 15 phút về tích phân',
    reason: 'Đề ngắn cho buổi tối bận, tập trung vào nguyên hàm – tích phân, chương bạn đang cải thiện tốt.',
    createdAt: daysAgo(1, 21, 15),
    durationMinutes: 15,
    chapters: ['12C4'],
    sections: [
      { id: 'p1', title: 'Phần 1: Trắc nghiệm', type: 'SINGLE_CHOICE', questionIds: ['q04', 'q05', 'q06'] },
      { id: 'p2', title: 'Phần 2: Đúng sai', type: 'TRUE_FALSE', questionIds: ['t02'] },
      { id: 'p3', title: 'Phần 3: Trả lời ngắn', type: 'SHORT_ANSWER', questionIds: ['s01'] },
    ],
  },
];

const byId = new Map(questions.map((q) => [q.id, q]));

interface AttemptPlan {
  id: string;
  examId: string;
  day: number;
  minutes: number;
  wrong: string[];
  skipped?: string[];
}

/** Lịch sử làm bài: điểm tăng dần, chương 12C1 yếu lúc đầu rồi khá lên. */
const plans: AttemptPlan[] = [
  { id: 'lan-1', examId: 'de-tong-hop-thpt', day: 26, minutes: 58, wrong: ['q02', 'q03', 'q06', 'q09', 'q12', 't01', 't02', 's02'], skipped: ['s01', 's03'] },
  { id: 'lan-2', examId: 'de-mu-logarit-khong-gian', day: 21, minutes: 22, wrong: ['q09', 's03', 't03'] },
  { id: 'lan-3', examId: 'de-ung-dung-dao-ham', day: 17, minutes: 29, wrong: ['q02', 'q03', 't01', 's02'], skipped: ['s01'] },
  { id: 'lan-4', examId: 'de-tong-hop-thpt', day: 13, minutes: 55, wrong: ['q02', 'q03', 'q06', 't01', 's02'], skipped: ['s04'] },
  { id: 'lan-5', examId: 'de-mu-logarit-khong-gian', day: 8, minutes: 19, wrong: ['q09', 's04'] },
  { id: 'lan-6', examId: 'de-ung-dung-dao-ham', day: 5, minutes: 26, wrong: ['q03', 't02'] },
  { id: 'lan-7', examId: 'de-tong-hop-thpt', day: 2, minutes: 52, wrong: ['q06', 'q11', 't03'] },
  { id: 'lan-8', examId: 'de-ung-dung-dao-ham', day: 0, minutes: 24, wrong: ['s02'] },
];

/** Băm chuỗi thành số 0..1 ổn định, để thời gian mẫu không đổi giữa các lần tải. */
const unit = (key: string) => {
  let h = 2166136261;
  for (const ch of key) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return ((h >>> 0) % 1000) / 1000;
};

/**
 * Thời gian mẫu cho từng câu (synthetic, chỉ để demo biểu đồ nhịp độ): chia tổng thời gian lượt làm
 * theo trọng số dạng câu × mức độ, nhân thêm dao động ngẫu nhiên cố định; câu sai và bỏ trống nặng hơn.
 */
function sampleSeconds(plan: AttemptPlan, ids: string[]): Record<string, number> {
  const typeW = { SINGLE_CHOICE: 1, TRUE_FALSE: 2.2, SHORT_ANSWER: 2.6, MULTIPLE_CHOICE: 1.5, ESSAY: 3 } as const;
  const diffW = { NB: 0.7, TH: 1, VD: 1.5, VDC: 2 } as const;
  const weights = ids.map((id) => {
    const q = byId.get(id)!;
    const struggle = plan.skipped?.includes(id) ? 1.6 : plan.wrong.includes(id) ? 1.35 : 1;
    return typeW[q.type] * diffW[q.difficulty] * struggle * (0.65 + unit(`${plan.id}:${id}`) * 0.8);
  });
  const sum = weights.reduce((a, b) => a + b, 0);
  return Object.fromEntries(ids.map((id, i) => [id, Math.max(8, Math.round((weights[i] / sum) * plan.minutes * 60))]));
}

export const seedAttempts = (exams: Exam[]): Attempt[] =>
  plans.map((plan) => {
    const exam = exams.find((e) => e.id === plan.examId);
    if (!exam) throw new Error(`Thiếu đề ${plan.examId}`);
    const answers: Record<string, Answer> = {};
    for (const id of exam.sections.flatMap((s) => s.questionIds)) {
      const q = byId.get(id);
      if (!q || plan.skipped?.includes(id)) continue;
      answers[id] = plan.wrong.includes(id) ? wrongAnswer(q) : correctAnswer(q);
    }
    const graded = gradeExam(exam, byId, answers);
    const submittedAt = daysAgo(plan.day, 20, 30);
    return {
      id: plan.id,
      examId: plan.examId,
      startedAt: new Date(new Date(submittedAt).getTime() - plan.minutes * 60_000).toISOString(),
      submittedAt,
      durationSeconds: plan.minutes * 60,
      answers,
      questionSeconds: sampleSeconds(plan, exam.sections.flatMap((s) => s.questionIds).filter((id) => byId.has(id))),
      score: graded.score,
      correct: graded.correct,
      total: graded.total,
    };
  });

/** Ngày có học (làm đề hoặc luyện câu lẻ), tính lùi từ hôm nay. Hôm nay đến 5 ngày trước liên tục. */
export const seedStudyDays = [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 15, 17, 18, 21, 22, 26, 27, 30, 34, 35, 41, 47, 48, 52, 61, 66, 70];
