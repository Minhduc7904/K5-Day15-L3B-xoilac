import { isAxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { adaptDraft, type ServerDraft } from './exam-chat-api';
import type { QuestionResult } from './grading';
import type { Answer, Attempt } from './types';

export type AttemptSummary = {
  attempt_id: number;
  draft_id: number;
  status: 'in_progress' | 'graded';
  started_at: string;
  deadline_at: string | null;
  finished_at: string | null;
  reason: 'manual' | 'timeout' | null;
  revision: number;
  answers: Record<string, { value: Answer; revision: number }>;
  question_seconds: Record<string, number>;
  current: string | null;
  score: number | null;
  correct?: number;
  total?: number;
};

export type AttemptState = AttemptSummary & { server_now: string; draft: ServerDraft };

export type AttemptUpdate = {
  mutation_id: string;
  question: string;
  answer?: Answer;
  base_revision?: number;
  tab_id?: string;
  elapsed_ms?: number;
  current?: string;
  release_tab?: boolean;
};

export class AttemptSyncError extends Error {
  constructor(readonly code: string, message: string) {
    super(message);
  }
}

export function attemptError(error: unknown) {
  if (error instanceof AttemptSyncError) return error;
  const detail = isAxiosError(error) ? error.response?.data?.detail : null;
  if (detail?.code) return new AttemptSyncError(detail.code, detail.message);
  return new AttemptSyncError('NETWORK', 'Chưa kết nối được máy chủ. Bạn thử lại nhé.');
}

const examPath = (id: string) => `/study/exams/${id.replace(/^draft-/, '')}/attempts`;
const attemptPath = (id: number) => `/study/attempts/${id}`;
export const attemptResultId = (id: number) => `online-${id}`;
export const answerValues = (state: AttemptSummary) =>
  Object.fromEntries(Object.entries(state.answers).map(([id, entry]) => [id, entry.value]));

export function adaptAttempt(summary: AttemptSummary): Attempt {
  return {
    id: attemptResultId(summary.attempt_id), examId: `draft-${summary.draft_id}`,
    startedAt: summary.started_at, submittedAt: summary.finished_at ?? summary.started_at,
    durationSeconds: Math.max(0, Math.floor((Date.parse(summary.finished_at ?? summary.started_at)
      - Date.parse(summary.started_at)) / 1000)),
    answers: answerValues(summary), questionSeconds: summary.question_seconds,
    score: summary.score ?? 0, correct: summary.correct ?? 0, total: summary.total ?? 0,
    reason: summary.reason ?? undefined,
  };
}

type ResultResponse = {
  attempt: AttemptSummary;
  previous: AttemptSummary | null;
  draft: ServerDraft;
  grading: { score: number; results: { code: string; points: number; status: QuestionResult['status']; tf_correct: number | null }[] };
  keys: Record<string, { answer: string | null; solution: string | null; statements: boolean[] }>;
};

export type ExamAttemptSummary = { active: boolean; count: number; best_score: number | null; last_at: string | null };

export const attemptApi = {
  async summaries() {
    return (await apiClient.get<Record<string, ExamAttemptSummary>>('/study/attempts')).data;
  },
  async overview(id: string) {
    return (await apiClient.get<{ latest: AttemptSummary | null; history: AttemptSummary[] }>(examPath(id))).data;
  },
  async start(id: string, restart: boolean) {
    return (await apiClient.post<AttemptState>(examPath(id), { restart })).data;
  },
  async read(id: number) {
    return (await apiClient.get<AttemptState>(attemptPath(id))).data;
  },
  async save(id: number, update: AttemptUpdate) {
    return (await apiClient.patch<AttemptState>(attemptPath(id), update)).data;
  },
  async submit(id: number) {
    return (await apiClient.post<AttemptState>(attemptPath(id) + '/submit')).data;
  },
  async result(id: number) {
    const { data } = await apiClient.get<ResultResponse>(attemptPath(id) + '/result');
    const { exam, questions } = adaptDraft(data.draft);
    const questionById = new Map(questions.map((q) => [q.id, q]));
    const gradedById = new Map(data.grading.results.map((entry) => [entry.code, entry]));
    const attempt = adaptAttempt(data.attempt);
    const results: QuestionResult[] = exam.sections.flatMap((section) => section.questionIds.map((code) => {
      const question = questionById.get(code)!;
      const grade = gradedById.get(code)!;
      const key = data.keys[code];
      return {
        question: { ...question, remoteAttemptId: id, answer: key.answer ?? undefined, solution: key.solution ?? undefined,
          statements: question.statements.map((option, index) => ({ ...option, correct: key.statements[index] })) },
        answer: attempt.answers[code] ?? null, points: grade.points, max: question.maxPoints ?? 0,
        status: grade.status, tfCorrect: grade.tf_correct ?? undefined,
      };
    }));
    const graded = { results, score: attempt.score, correct: attempt.correct, total: attempt.total };
    return { attempt, exam, graded, previous: data.previous ? adaptAttempt(data.previous) : undefined };
  },
};
