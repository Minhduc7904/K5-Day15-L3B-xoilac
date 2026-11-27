/**
 * API giả lập cho phần học sinh, chạy trong trình duyệt. Dữ liệu người dùng tạo thêm (đề, lượt làm,
 * hồ sơ) lưu ở localStorage key `examind:mock-study`, gộp với dữ liệu mẫu trong `fixtures/`.
 * Xoá bằng `resetMockData()` (nút "Khôi phục dữ liệu mẫu" ở trang hồ sơ).
 */
import { allocate, defaultPlan, parentOf, planFromRows, planTotal, rescaleChapters, rescaleTypes, MAX_QUESTIONS, type ExamPlan } from './create/plan';
import { chapterOf } from './fixtures/chapters';
import { questions } from './fixtures/questions';
import { seedAttempts, seedExams, seedProfile, seedStudyDays } from './fixtures/seed';
import { gradeExam } from './grading';
import type {
  Answer,
  Attempt,
  ChapterStat,
  DashboardData,
  Exam,
  ExamSection,
  ExamSummary,
  PublicQuestion,
  CreditLedgerEntry,
  CreditSummary,
  Question,
  StructureProposal,
  StudentProfile,
} from './types';

const STORAGE_KEY = 'examind:mock-study';
const MONTHLY_CREDITS = 500;
const DAY = 24 * 60 * 60 * 1000;

interface Store {
  exams: Exam[];
  attempts: Attempt[];
  profile: StudentProfile | null;
}

const empty = (): Store => ({ exams: [], attempts: [], profile: null });

function load(): Store {
  if (typeof window === 'undefined') return empty();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...empty(), ...(JSON.parse(raw) as Store) } : empty();
  } catch {
    return empty();
  }
}

function save(store: Store) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Hết dung lượng hoặc chế độ riêng tư: dữ liệu chỉ còn trong phiên hiện tại.
  }
}

export const delay = (ms = 500) => new Promise((resolve) => window.setTimeout(resolve, ms));

export const questionsById = new Map(questions.map((q) => [q.id, q]));

const allExams = () => {
  const seeded = seedExams();
  return [...load().exams, ...seeded];
};

const allAttempts = (exams: Exam[]) =>
  [...seedAttempts(exams), ...load().attempts].sort((a, b) => a.submittedAt.localeCompare(b.submittedAt));

const toPublic = (q: Question): PublicQuestion => ({
  id: q.id,
  type: q.type,
  difficulty: q.difficulty,
  chapter: q.chapter,
  content: q.content,
  statements: q.statements.map(({ label, content }) => ({ label, content })),
});

class NotFoundError extends Error {
  constructor(what: string) {
    super(`Không tìm thấy ${what}`);
    this.name = 'NotFoundError';
  }
}

const dayKey = (iso: string | number) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

function chapterStats(exams: Exam[], attempts: Attempt[]): ChapterStat[] {
  const map = new Map<string, { correct: number; total: number }>();
  for (const attempt of attempts) {
    const exam = exams.find((e) => e.id === attempt.examId);
    if (!exam) continue;
    for (const r of gradeExam(exam, questionsById, attempt.answers).results) {
      const entry = map.get(r.question.chapter) ?? { correct: 0, total: 0 };
      entry.total += 1;
      if (r.status === 'correct') entry.correct += 1;
      map.set(r.question.chapter, entry);
    }
  }
  return [...map.entries()].map(([code, v]) => ({ chapter: chapterOf(code), ...v }));
}

function streakFrom(attempts: Attempt[]) {
  const studied = new Set([
    ...seedStudyDays.map((n) => dayKey(Date.now() - n * DAY)),
    ...attempts.map((a) => dayKey(a.submittedAt)),
  ]);
  const today = Date.now();
  // Chuỗi hiện tại: tính từ hôm nay (hoặc hôm qua nếu hôm nay chưa học) lùi về.
  let start = studied.has(dayKey(today)) ? 0 : 1;
  let current = 0;
  while (studied.has(dayKey(today - (start + current) * DAY))) current += 1;
  if (current === 0) start = 0;

  let best = 0;
  let run = 0;
  for (let n = 120; n >= 0; n -= 1) {
    run = studied.has(dayKey(today - n * DAY)) ? run + 1 : 0;
    best = Math.max(best, run);
  }
  // 12 tuần gần nhất, cũ → mới, cho lịch nhiệt ở trang hồ sơ và 7 ngày trên dashboard.
  const days = Array.from({ length: 84 }, (_, i) => {
    const t = today - (83 - i) * DAY;
    return { date: new Date(t).toISOString(), studied: studied.has(dayKey(t)) };
  });
  return { current, best, days };
}

/* ---------------- Agent giả lập ---------------- */

const KEYWORDS: Array<[RegExp, string]> = [
  [/khảo sát|cực trị|đơn điệu|tiệm cận|đồng biến|nghịch biến|ứng dụng đạo hàm|gtln|gtnn|max|min/i, '12C1'],
  [/tích phân|nguyên hàm|diện tích hình phẳng/i, '12C4'],
  [/mũ|lôgarit|logarit|log/i, '11C6'],
  [/không gian|hình chóp|vuông góc|lăng trụ/i, '11C7'],
  [/toạ độ|tọa độ|oxyz|mặt phẳng|mặt cầu/i, '12C5'],
  [/xác suất|tổ hợp|bi đỏ/i, '10C9'],
  [/số liệu|ghép nhóm|phương sai|độ lệch/i, '12C3'],
  [/\bđạo hàm\b/i, '11C9'],
];

const OFF_TOPIC = /(ngữ văn|tiếng anh|vật lý|hoá học|hóa học|sinh học|lịch sử|địa lý)/i;
const CHEAT = /(đáp án (của )?(đề|bài) (đang|kiểm tra|thi)|sửa điểm|nâng điểm|bỏ qua hướng dẫn|ignore)/i;

export const poolSize = (chapter: string, type: Question['type']) =>
  questions.filter((q) => q.chapter === chapter && q.type === type).length;

function weakestChapters(): string[] {
  const exams = allExams();
  const stats = chapterStats(exams, allAttempts(exams))
    .filter((s) => s.total >= 3)
    .sort((a, b) => a.correct / a.total - b.correct / b.total);
  return stats.slice(0, 2).map((s) => s.chapter.code);
}

function proposalFor(codes: string[], minutes: number, reason: string): StructureProposal {
  const names = codes.map((c) => chapterOf(c).name);
  return {
    title: codes.length === 1 ? `Ôn ${names[0]}` : `Ôn ${names.join(' + ')}`,
    reason,
    durationMinutes: minutes,
    rows: allocate(defaultPlan(codes, minutes)),
  };
}

export type AgentEvent =
  | { kind: 'text'; text: string }
  | { kind: 'proposal'; proposal: StructureProposal }
  | { kind: 'built'; exam: Exam; shortages: string[] };

export interface AgentInput {
  message: string;
  imageCount: number;
  proposal: StructureProposal | null;
  /** Học sinh chỉnh tổng quan (chương, dạng, độ khó) và nhờ agent phân bổ lại ma trận. */
  plan?: ExamPlan | null;
}

/** Trả lời theo từng đoạn như model thật đang stream. Quy tắc bám spec §4 và §6. */
export async function* runAgent({ message, imageCount, proposal, plan }: AgentInput): AsyncGenerator<AgentEvent> {
  const say = async function* (text: string): AsyncGenerator<AgentEvent> {
    for (const part of text.match(/\S+\s*/g) ?? []) {
      await delay(28 + Math.random() * 40);
      yield { kind: 'text', text: part };
    }
  };
  await delay(900 + Math.random() * 600);
  const text = message.trim();

  if (CHEAT.test(text)) {
    yield* say('Mình không đưa đáp án của đề đang thi hay kiểm tra, cũng không sửa điểm được. Nhưng mình có thể ra một đề ôn đúng phần đó để bạn luyện trước nhé!');
    return;
  }
  if (OFF_TOPIC.test(text)) {
    yield* say('Hiện mình chỉ hỗ trợ môn Toán THPT thôi. Bạn muốn ôn chương Toán nào? Hoặc bấm "Ôn chương yếu" để mình tự chọn theo lịch sử làm bài.');
    return;
  }

  if (proposal && plan) {
    const rows = allocate(plan);
    const subCount = new Set(rows.map((r) => r.chapter)).size;
    yield* say(`Mình đã phân bổ lại ma trận: ${planTotal(plan)} câu chia cho ${subCount} chương con, giữ đúng số câu mỗi chương, mỗi dạng và tỉ lệ độ khó bạn chọn. Bấm "Nâng cao" nếu muốn chỉnh từng ô.`);
    yield { kind: 'proposal', proposal: { ...proposal, rows } };
    return;
  }

  if (proposal && /(xác nhận|đồng ý|ok|tạo đề|dựng đề|được rồi|chốt)/i.test(text)) {
    yield* say('Tuyệt! Mình đang chọn câu đã được duyệt trong ngân hàng theo đúng cấu trúc bạn chốt…');
    const built = buildExam(proposal);
    yield* say(
      built.shortages.length
        ? ` Đã dựng xong đề, nhưng ngân hàng còn thiếu: ${built.shortages.join('; ')}. Mình chỉ đưa câu có thật, không tự viết thêm.`
        : ' Đã dựng xong đề nháp, đủ số câu. Bạn xem lại rồi bắt đầu làm khi sẵn sàng nhé!',
    );
    yield { kind: 'built', exam: built.exam, shortages: built.shortages };
    return;
  }

  if (proposal && /(thêm|bớt|giảm|tăng|khó hơn|dễ hơn|\d+\s*phút)/i.test(text)) {
    const next = adjust(proposal, text);
    yield* say('Mình đã cập nhật cấu trúc theo ý bạn. Xem bảng bên cạnh, chỉnh tiếp hoặc bấm "Dựng đề" khi ưng nhé.');
    yield { kind: 'proposal', proposal: next };
    return;
  }

  const minutes = /không giới hạn|vô hạn/i.test(text) ? 0 : Number(text.match(/(\d{1,3})\s*phút/i)?.[1]) || 30;
  const picked = [...new Set(KEYWORDS.filter(([re]) => re.test(text)).map(([, code]) => code))].slice(0, 2);
  const imageNote = imageCount
    ? `Mình đã nhận ${imageCount} ảnh. (Bản mock chưa đọc nội dung ảnh, bản thật sẽ nhận diện chương từ ảnh.) `
    : '';

  if (picked.length) {
    const names = picked.map((c) => chapterOf(c).name).join(' và ');
    yield* say(`${imageNote}Mình hiểu bạn muốn ôn **${names}**. Dưới đây là cấu trúc đề ${minutes ? `${minutes} phút` : 'không giới hạn thời gian'} mình đề xuất, bạn xem trước và chỉnh nếu cần nhé.`);
    yield {
      kind: 'proposal',
      proposal: proposalFor(picked, minutes, `Bạn chọn ${names}. Mỗi chương có đủ ba dạng câu để ôn như đề thật, độ khó chủ yếu Thông hiểu – Vận dụng.`),
    };
    return;
  }

  const weak = weakestChapters();
  if (!weak.length) {
    yield* say(`${imageNote}Mình chưa có đủ lịch sử làm bài để biết chương nào bạn hay sai. Bạn muốn ôn chương nào? Ví dụ: "ôn tích phân 20 phút".`);
    return;
  }
  const stats = chapterStats(allExams(), allAttempts(allExams()));
  const detail = weak
    .map((code) => {
      const s = stats.find((x) => x.chapter.code === code);
      return s ? `${s.chapter.name} (đúng ${s.correct}/${s.total} câu)` : code;
    })
    .join(' và ');
  yield* say(`${imageNote}Dựa trên các lượt làm bài gần đây, hai chương bạn hay sai nhất là **${detail}**. Mình đề xuất đề ${minutes ? `${minutes} phút` : 'không giới hạn thời gian'} dồn vào hai chương này:`);
  yield {
    kind: 'proposal',
    proposal: proposalFor(weak, minutes, `Theo lịch sử làm bài: ${detail}. Chia câu cho cả hai chương vì tỉ lệ đúng gần nhau.`),
  };
}

function adjust(proposal: StructureProposal, text: string): StructureProposal {
  const n = Number(text.match(/(\d+)\s*câu/i)?.[1]) || 1;
  const minutes = /không giới hạn|vô hạn/i.test(text) ? 0 : Number(text.match(/(\d{1,3})\s*phút/i)?.[1]);
  const sign = /(bớt|giảm)/i.test(text) ? -1 : /(thêm|tăng)/i.test(text) ? 1 : 0;
  const plan = planFromRows(proposal.rows);
  const total = Math.max(1, Math.min(MAX_QUESTIONS, planTotal(plan) + sign * n));
  const shift = /khó hơn/i.test(text) ? 10 : /dễ hơn/i.test(text) ? -10 : 0;
  const difficulty = { ...plan.difficulty };
  if (shift > 0) {
    const take = Math.min(shift, difficulty.NB + difficulty.TH);
    const fromNb = Math.min(take, difficulty.NB);
    difficulty.NB -= fromNb;
    difficulty.TH -= take - fromNb;
    difficulty.VD += Math.ceil(take / 2);
    difficulty.VDC += Math.floor(take / 2);
  } else if (shift < 0) {
    const take = Math.min(-shift, difficulty.VD + difficulty.VDC);
    const fromVdc = Math.min(take, difficulty.VDC);
    difficulty.VDC -= fromVdc;
    difficulty.VD -= take - fromVdc;
    difficulty.NB += Math.ceil(take / 2);
    difficulty.TH += Math.floor(take / 2);
  }
  const next: ExamPlan = { chapters: rescaleChapters(plan.chapters, total), types: rescaleTypes(plan.types, total), difficulty };
  return {
    ...proposal,
    durationMinutes: Number.isFinite(minutes) ? minutes : proposal.durationMinutes,
    rows: sign || shift ? allocate(next) : proposal.rows,
  };
}

const sectionMeta = {
  SINGLE_CHOICE: { id: 'p1', title: 'Phần 1: Trắc nghiệm' },
  TRUE_FALSE: { id: 'p2', title: 'Phần 2: Đúng sai' },
  SHORT_ANSWER: { id: 'p3', title: 'Phần 3: Trả lời ngắn' },
} as const;

function buildExam(proposal: StructureProposal) {
  const missing = new Map<string, { need: number; got: number }>();
  const used = new Set<string>();
  const sections: ExamSection[] = (['SINGLE_CHOICE', 'TRUE_FALSE', 'SHORT_ANSWER'] as const)
    .map((type) => {
      const ids: string[] = [];
      for (const row of proposal.rows.filter((r) => r.type === type)) {
        const pool = questions.filter((q) => (q.chapter === row.chapter || q.chapter === parentOf(row.chapter)) && q.type === type && !used.has(q.id));
        // Ưu tiên câu đúng độ khó, thiếu thì lấy câu cùng chương khác độ khó.
        pool.sort((a, b) => Number(b.difficulty === row.difficulty) - Number(a.difficulty === row.difficulty));
        const take = pool.slice(0, row.count);
        take.forEach((q) => used.add(q.id));
        ids.push(...take.map((q) => q.id));
        if (take.length < row.count) {
          const name = chapterOf(row.chapter).name;
          const m = missing.get(name) ?? { need: 0, got: 0 };
          missing.set(name, { need: m.need + row.count, got: m.got + take.length });
        }
      }
      return { ...sectionMeta[type], type, questionIds: ids };
    })
    .filter((s) => s.questionIds.length > 0);
  const shortages = [...missing].map(([name, m]) => `${name}: cần ${m.need} câu, chỉ có ${m.got}`);

  const exam: Exam = {
    id: `de-${Date.now().toString(36)}`,
    title: proposal.title,
    source: 'ai',
    reason: proposal.reason,
    createdAt: new Date().toISOString(),
    durationMinutes: proposal.durationMinutes,
    chapters: [...new Set(proposal.rows.map((r) => parentOf(r.chapter)))],
    sections,
  };
  const store = load();
  store.exams.unshift(exam);
  save(store);
  return { exam, shortages };
}

/* ---------------- API ---------------- */

export const mockStudyApi = {
  async getDashboard(): Promise<DashboardData> {
    await delay(650);
    const exams = allExams();
    const attempts = allAttempts(exams);
    const scores = attempts.map((a) => ({
      attemptId: a.id,
      examId: a.examId,
      title: exams.find((e) => e.id === a.examId)?.title ?? a.examId,
      date: a.submittedAt,
      score: a.score,
    }));
    return {
      streak: streakFrom(attempts),
      totals: {
        exams: new Set(attempts.map((a) => a.examId)).size,
        questions: attempts.reduce((s, a) => s + a.total, 0),
        minutes: Math.round(attempts.reduce((s, a) => s + a.durationSeconds, 0) / 60),
        average: attempts.length ? attempts.reduce((s, a) => s + a.score, 0) / attempts.length : null,
      },
      scores,
      chapters: chapterStats(exams, attempts).sort((a, b) => a.correct / a.total - b.correct / b.total),
      recent: [...attempts]
        .reverse()
        .slice(0, 5)
        .map((attempt) => ({ attempt, exam: exams.find((e) => e.id === attempt.examId)! })),
    };
  },

  async listExams(): Promise<ExamSummary[]> {
    await delay(550);
    const exams = allExams();
    const attempts = allAttempts(exams);
    return exams
      .map((exam) => {
        const mine = attempts.filter((a) => a.examId === exam.id);
        return {
          ...exam,
          questionCount: exam.sections.reduce((s, sec) => s + sec.questionIds.length, 0),
          attempts: mine.length,
          bestScore: mine.length ? Math.max(...mine.map((a) => a.score)) : null,
          lastAttemptAt: mine.at(-1)?.submittedAt ?? null,
        };
      })
      .sort((a, b) => (b.lastAttemptAt ?? b.createdAt).localeCompare(a.lastAttemptAt ?? a.createdAt));
  },

  async getExam(id: string) {
    await delay(500);
    const exams = allExams();
    const exam = exams.find((e) => e.id === id);
    if (!exam) throw new NotFoundError('đề thi');
    const ids = exam.sections.flatMap((s) => s.questionIds);
    return {
      exam,
      questions: ids.map((qid) => toPublic(questionsById.get(qid)!)),
      attempts: allAttempts(exams).filter((a) => a.examId === id).reverse(),
    };
  },

  async submitAttempt(examId: string, answers: Record<string, Answer>, startedAt: string, questionSeconds?: Record<string, number>): Promise<Attempt> {
    await delay(900);
    const exam = allExams().find((e) => e.id === examId);
    if (!exam) throw new NotFoundError('đề thi');
    const graded = gradeExam(exam, questionsById, answers);
    const submittedAt = new Date().toISOString();
    const attempt: Attempt = {
      id: `lan-${Date.now().toString(36)}`,
      examId,
      startedAt,
      submittedAt,
      durationSeconds: Math.max(1, Math.round((Date.parse(submittedAt) - Date.parse(startedAt)) / 1000)),
      answers,
      questionSeconds,
      score: graded.score,
      correct: graded.correct,
      total: graded.total,
    };
    const store = load();
    store.attempts.push(attempt);
    save(store);
    return attempt;
  },

  /** Kết quả kèm đáp án và lời giải. Chỉ trả sau khi đã nộp bài. */
  async getResult(attemptId: string) {
    await delay(600);
    const exams = allExams();
    const attempt = allAttempts(exams).find((a) => a.id === attemptId);
    if (!attempt) throw new NotFoundError('lượt làm bài');
    const exam = exams.find((e) => e.id === attempt.examId);
    if (!exam) throw new NotFoundError('đề thi');
    const previous = allAttempts(exams).filter((a) => a.examId === exam.id && a.submittedAt < attempt.submittedAt).at(-1) ?? null;
    return { attempt, exam, graded: gradeExam(exam, questionsById, attempt.answers), previous };
  },

  async getProfile(): Promise<{ profile: StudentProfile; dashboard: DashboardData }> {
    const [dashboard] = await Promise.all([mockStudyApi.getDashboard()]);
    return { profile: load().profile ?? seedProfile(), dashboard };
  },

  async updateProfile(profile: StudentProfile): Promise<StudentProfile> {
    await delay(700);
    const store = load();
    store.profile = profile;
    save(store);
    return profile;
  },

  /** Mỗi đề AI tạo trong tháng trừ 1 credit, hạn mức 30 credit/tháng (số tự đặt cho bản mock). */
  async getCredits(): Promise<CreditSummary> {
    await delay(200);
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const resetsAt = new Date(now.getFullYear(), now.getMonth() + 1, 1).toISOString();
    const used = allExams()
      .filter((e) => e.source === 'ai' && Date.parse(e.createdAt) >= monthStart.getTime())
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    const history: CreditLedgerEntry[] = [
      ...used.map((e) => ({ id: `use-${e.id}`, date: e.createdAt, label: `Tạo đề “${e.title}”`, amount: -1 })),
      { id: `grant-${monthStart.toISOString()}`, date: monthStart.toISOString(), label: `Hạn mức tháng ${now.getMonth() + 1}`, amount: MONTHLY_CREDITS },
    ];
    return { balance: Math.max(0, MONTHLY_CREDITS - used.length), monthlyQuota: MONTHLY_CREDITS, usedThisMonth: used.length, resetsAt, history };
  },

  resetMockData() {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
      Object.keys(window.localStorage)
        .filter((k) => k.startsWith('examind:attempt-draft:'))
        .forEach((k) => window.localStorage.removeItem(k));
    } catch {
      // Bỏ qua: không có quyền truy cập bộ nhớ.
    }
  },
};

export { NotFoundError };
