import { apiClient } from '@/lib/api-client';
import { attemptResultId } from './attempt-api';
import type { Attempt, DashboardData, Exam } from './types';

type ServerDashboard = {
  streak: DashboardData['streak'];
  totals: DashboardData['totals'];
  scores: Array<{ attempt_id: number; draft_id: number; title: string; date: string; score: number }>;
  chapters: Array<{ code: string; name: string; grade: number | null; correct: number; total: number }>;
  recent: Array<{
    attempt: {
      attempt_id: number; started_at: string; finished_at: string; duration_seconds: number; score: number;
      correct: number; total: number; answered: number; reason: 'manual' | 'timeout' | null;
    };
    exam: { draft_id: number; title: string; duration_minutes: number; question_count: number };
  }>;
};

const examId = (draftId: number) => `draft-${draftId}`;

export function adaptDashboard(data: ServerDashboard): DashboardData {
  return {
    streak: data.streak,
    totals: data.totals,
    scores: data.scores.map((s) => ({
      attemptId: attemptResultId(s.attempt_id), examId: examId(s.draft_id), title: s.title, date: s.date, score: s.score,
    })),
    chapters: data.chapters.map((c) => ({
      chapter: { code: c.code, name: c.name, grade: (c.grade === 10 || c.grade === 11 ? c.grade : 12) },
      correct: c.correct, total: c.total,
    })),
    recent: data.recent.map(({ attempt, exam }) => ({
      attempt: {
        id: attemptResultId(attempt.attempt_id), examId: examId(exam.draft_id), startedAt: attempt.started_at,
        submittedAt: attempt.finished_at, durationSeconds: attempt.duration_seconds, answers: {}, score: attempt.score,
        correct: attempt.correct, total: attempt.total, answered: attempt.answered, reason: attempt.reason ?? undefined,
      } satisfies Attempt,
      exam: {
        id: examId(exam.draft_id), title: exam.title, source: 'ai', createdAt: attempt.started_at,
        durationMinutes: exam.duration_minutes, chapters: [], sections: [],
      } satisfies Exam,
    })),
  };
}

export const dashboardApi = {
  async get(): Promise<DashboardData> {
    return adaptDashboard((await apiClient.get<ServerDashboard>('/study/dashboard')).data);
  },
};
