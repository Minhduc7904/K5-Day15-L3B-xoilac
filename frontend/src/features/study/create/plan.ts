/**
 * Kế hoạch đề ở dạng tổng quan (số câu mỗi chương cha, số câu mỗi dạng, % mỗi mức độ)
 * và cách chuyển qua lại với ma trận chi tiết (chương con × dạng × mức độ) trong `StructureProposal.rows`.
 */
import { chapterOf, chapters } from '../fixtures/chapters';
import { subchapters } from '../fixtures/subchapters';
import type { Chapter, Difficulty, QuestionType, StructureRow } from '../types';

export const MAX_QUESTIONS = 50;
export const TYPES: QuestionType[] = ['SINGLE_CHOICE', 'TRUE_FALSE', 'SHORT_ANSWER'];
export const DIFFS: Difficulty[] = ['NB', 'TH', 'VD', 'VDC'];

export interface ExamPlan {
  /** Chương cha và số câu. Tổng bằng tổng số câu các dạng. */
  chapters: Array<{ code: string; count: number }>;
  types: Record<QuestionType, number>;
  /** Phần trăm từng mức độ, tổng 100. */
  difficulty: Record<Difficulty, number>;
}

const subByCode = new Map(subchapters.map((s) => [s.code, s]));

/** Mã chương cha của một chương con. Chương cha trả về chính nó. */
export const parentOf = (code: string) => subByCode.get(code)?.parent ?? code;

/** Chương con của một chương cha; chương chưa có chương con thì coi chính nó là một dòng. */
export function subchaptersOf(parent: string): Chapter[] {
  const subs = subchapters.filter((s) => s.parent === parent);
  return subs.length ? subs : [chapterOf(parent)];
}

export const parentChapters = chapters;

/** Chia `total` theo trọng số, phần dư chia cho phần lẻ lớn nhất. Trọng số toàn 0 thì chia đều. */
export function distribute(total: number, weights: number[]): number[] {
  if (!weights.length) return [];
  const sum = weights.reduce((s, w) => s + w, 0);
  const safe = sum > 0 ? weights : weights.map(() => 1);
  const safeSum = sum > 0 ? sum : weights.length;
  const raw = safe.map((w) => (w / safeSum) * total);
  const out = raw.map(Math.floor);
  let left = total - out.reduce((s, n) => s + n, 0);
  const order = raw.map((r, i) => ({ i, frac: r - Math.floor(r) })).sort((a, b) => b.frac - a.frac);
  for (let k = 0; left > 0; k = (k + 1) % order.length, left--) out[order[k].i]++;
  return out;
}

export const planTotal = (plan: ExamPlan) => TYPES.reduce((s, t) => s + plan.types[t], 0);

export function planFromRows(rows: StructureRow[]): ExamPlan {
  const chapterCounts = new Map<string, number>();
  const types = { SINGLE_CHOICE: 0, TRUE_FALSE: 0, SHORT_ANSWER: 0, MULTIPLE_CHOICE: 0, ESSAY: 0 };
  const diffCounts = { NB: 0, TH: 0, VD: 0, VDC: 0 } as Record<Difficulty, number>;
  for (const row of rows) {
    const parent = parentOf(row.chapter);
    chapterCounts.set(parent, (chapterCounts.get(parent) ?? 0) + row.count);
    types[row.type] += row.count;
    diffCounts[row.difficulty] += row.count;
  }
  // Làm tròn theo bước 5% cho khớp thanh kéo độ khó.
  const pct = distribute(20, DIFFS.map((d) => diffCounts[d])).map((n) => n * 5);
  return {
    chapters: [...chapterCounts].map(([code, count]) => ({ code, count })),
    types,
    difficulty: Object.fromEntries(DIFFS.map((d, i) => [d, pct[i]])) as Record<Difficulty, number>,
  };
}

/** Đổi tổng số câu, giữ tỉ lệ giữa các chương. */
export function rescaleChapters(list: ExamPlan['chapters'], total: number): ExamPlan['chapters'] {
  const next = distribute(total, list.map((c) => c.count));
  return list.map((c, i) => ({ ...c, count: next[i] }));
}

/** Đổi tổng số câu, giữ tỉ lệ giữa các dạng. */
export function rescaleTypes(types: ExamPlan['types'], total: number): ExamPlan['types'] {
  const next = distribute(total, TYPES.map((t) => types[t]));
  return Object.fromEntries(TYPES.map((t, i) => [t, next[i]])) as ExamPlan['types'];
}

/**
 * Phân bổ kế hoạch tổng quan thành ma trận chi tiết.
 * Câu xếp theo dạng (Trắc nghiệm → Đúng sai → Trả lời ngắn) và mức độ tăng dần, nên câu dễ rơi vào phần đầu
 * như đề thật. Chương xen kẽ để chương nào cũng có đủ dạng, trong chương thì xoay vòng các chương con.
 */
export function allocate(plan: ExamPlan): StructureRow[] {
  const total = planTotal(plan);
  if (total === 0) return [];
  const chaptersList = rescaleChapters(plan.chapters.length ? plan.chapters : [{ code: '12C1', count: 1 }], total);

  const typeSlots = TYPES.flatMap((t) => Array<QuestionType>(plan.types[t]).fill(t));
  const diffCounts = distribute(total, DIFFS.map((d) => plan.difficulty[d]));
  const diffSlots = DIFFS.flatMap((d, i) => Array<Difficulty>(diffCounts[i]).fill(d));

  const remaining = chaptersList.map((c) => c.count);
  const chapterSlots: string[] = [];
  for (let i = 0; chapterSlots.length < total; i = (i + 1) % chaptersList.length) {
    if (remaining[i] > 0) {
      chapterSlots.push(chaptersList[i].code);
      remaining[i]--;
    }
  }

  const cursor = new Map<string, number>();
  const cells = new Map<string, StructureRow>();
  for (let i = 0; i < total; i++) {
    const parent = chapterSlots[i];
    const subs = subchaptersOf(parent);
    const k = cursor.get(parent) ?? 0;
    cursor.set(parent, k + 1);
    const chapter = subs[k % subs.length].code;
    const key = `${chapter}|${typeSlots[i]}|${diffSlots[i]}`;
    const cell = cells.get(key);
    if (cell) cell.count++;
    else cells.set(key, { chapter, type: typeSlots[i], difficulty: diffSlots[i], count: 1 });
  }
  return [...cells.values()];
}

/** Kế hoạch mặc định theo thời lượng: tỉ lệ dạng câu bám cấu trúc đề tốt nghiệp (12 : 4 : 6). */
export function defaultPlan(codes: string[], minutes: number): ExamPlan {
  const total = Math.min(MAX_QUESTIONS, Math.max(6, minutes > 0 ? Math.round(minutes * 0.45) + 2 : 16));
  const [sc, tf, sa] = distribute(total, [12, 4, 6]);
  return {
    chapters: codes.map((code, i) => ({ code, count: distribute(total, codes.map(() => 1))[i] })),
    types: { SINGLE_CHOICE: sc, TRUE_FALSE: tf, SHORT_ANSWER: sa, MULTIPLE_CHOICE: 0, ESSAY: 0 },
    difficulty: { NB: 30, TH: 35, VD: 25, VDC: 10 },
  };
}

export const sameRows = (a: StructureRow[], b: StructureRow[]) => {
  const key = (rows: StructureRow[]) => rows.filter((r) => r.count > 0).map((r) => `${r.chapter}|${r.type}|${r.difficulty}|${r.count}`).sort().join(',');
  return key(a) === key(b);
};
