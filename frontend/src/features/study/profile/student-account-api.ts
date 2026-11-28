import { apiClient } from '@/lib/api-client';

export const EXAM_PERIODS = {
  midterm_1: 'Giữa kỳ 1',
  final_1: 'Cuối kỳ 1',
  midterm_2: 'Giữa kỳ 2',
  final_2: 'Cuối kỳ 2',
  national_high_school: 'THPT Quốc gia',
} as const;
export type ExamPeriod = keyof typeof EXAM_PERIODS;

export interface ProfileInput {
  school_name: string;
  grade: number;
  target_score: number;
  exam_period: ExamPeriod;
  study_days: number[];
  reminder_time: string | null;
  display_name?: string;
}

export interface StudentProfile extends Omit<ProfileInput, 'display_name'> {
  display_name: string | null;
  email: string;
  email_verified: boolean;
  joined_at: string;
}

export interface ProfileStatus {
  completed: boolean;
  profile: StudentProfile | null;
  email_verified: boolean;
}

export interface CreditEntry {
  id: number;
  delta: number;
  balance_after: number;
  reason: string;
  effective_on: string;
  created_at: string;
}

export interface CreditSummary {
  balance: number;
  limit: number;
  daily_grant: number;
  history: CreditEntry[];
  next_before_id: number | null;
}

const basePath = '/student/me';

export const studentAccountApi = {
  async getProfile(signal?: AbortSignal) {
    const { data } = await apiClient.get<ProfileStatus>(basePath + '/profile', { signal });
    return data;
  },
  async saveProfile(input: ProfileInput) {
    const { data } = await apiClient.put<StudentProfile>(basePath + '/profile', input);
    return data;
  },
  async getCredits(beforeId?: number, signal?: AbortSignal) {
    const { data } = await apiClient.get<CreditSummary>(basePath + '/credits', {
      params: { before_id: beforeId },
      signal,
    });
    return data;
  },
};
