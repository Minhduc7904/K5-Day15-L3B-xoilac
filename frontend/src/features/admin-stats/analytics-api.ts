/** Lớp gọi API phân tích cho dashboard admin: GET /api/v1/admin/stats/{overview,growth,learning,bank,operations}?range=7|30|90. */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';

export type RangeDays = 7 | 30 | 90;
export const RANGES: readonly RangeDays[] = [7, 30, 90];

export interface Kpi {
  key: string;
  value: number | null;
  previous: number | null;
  series: number[];
}

export interface Overview {
  range_days: number;
  generated_at: string;
  kpis: Kpi[];
  attention: { pending_pdf_drafts: number; draft_questions: number; failed_imports: number };
}

export interface Count {
  key: string;
  count: number;
}

export interface Growth {
  range_days: number;
  days: string[];
  signups: number[];
  dau: number[];
  wau: number[];
  active_students: number;
  stickiness: number | null;
  funnel: Array<{ key: string; label: string; count: number }>;
  heatmap: number[][];
  grades: Count[];
  targets: Count[];
}

export interface Learning {
  range_days: number;
  graded: number;
  median: number | null;
  average: number | null;
  bins: Array<{ label: string; count: number }>;
  weekly: Array<{ week: string; attempts: number; average: number | null }>;
  outcomes: Array<{ week: string; manual: number; timeout: number; in_progress: number }>;
  chapters: Array<{ code: string; name: string; correct: number; total: number; rate: number }>;
  chapters_hidden: number;
  min_answers: number;
}

export interface Bank {
  range_days: number;
  published: number;
  draft: number;
  private: number;
  archived: number;
  by_type: Count[];
  by_grade: Count[];
  by_difficulty: Count[];
  coverage: Array<{ code: string; name: string; grade: number | null; counts: Record<string, number>; total: number }>;
  shortages: {
    drafts: number;
    drafts_with_shortage: number;
    chapters: Array<{ code: string; name: string; missing: number; occurrences: number }>;
  };
}

export interface Operations {
  range_days: number;
  days: string[];
  imports: {
    total: number;
    success_rate: number | null;
    by_status: Count[];
    failed_by_stage: Count[];
    completed: number[];
    failed: number[];
    in_flight: number[];
  };
  pdf_drafts: Record<string, number>;
  credits: { granted: number[]; spent: number[] };
  chat: { sessions: number; with_draft: number; with_attempt: number; daily: number[] };
}

const get = <T>(name: string, range: RangeDays) =>
  request<T>(() => apiClient.get(`/admin/stats/${name}`, { withCredentials: true, params: { range } }));

export const adminAnalyticsApi = {
  overview: (range: RangeDays) => get<Overview>('overview', range),
  growth: (range: RangeDays) => get<Growth>('growth', range),
  learning: (range: RangeDays) => get<Learning>('learning', range),
  bank: (range: RangeDays) => get<Bank>('bank', range),
  operations: (range: RangeDays) => get<Operations>('operations', range),
};
