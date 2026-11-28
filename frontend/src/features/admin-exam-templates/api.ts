/**
 * Lớp gọi API mẫu cấu trúc đề của #5 (/api/v1/exam-templates) cho trang quản trị (#11).
 * Chỉ dùng API đã có; hợp đồng ở docs/api/exam-templates-api.md.
 * Lỗi nghiệp vụ 422 của #5 có `detail = {message, errors[]}`; `templateError` đổi thành một câu đọc được.
 */
import { isAxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { ApiError, request, toApiError } from '@/lib/api-error';

export type ExamType = 'GK1' | 'GK2' | 'CK1' | 'CK2' | 'THPT' | 'HSA' | 'TSA';
export type TemplateStatus = 'DRAFT' | 'APPROVED';
export type SectionType = 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'TRUE_FALSE' | 'SHORT_ANSWER' | 'ESSAY';
export type Difficulty = 'NB' | 'TH' | 'VD' | 'VDC';

export const EXAM_TYPES: Record<ExamType, string> = {
  GK1: 'Giữa kỳ 1', GK2: 'Giữa kỳ 2', CK1: 'Cuối kỳ 1', CK2: 'Cuối kỳ 2', THPT: 'Tốt nghiệp THPT', HSA: 'ĐGNL HSA', TSA: 'ĐGTD TSA',
};

export interface TemplateSection {
  order: number;
  title: string;
  question_type: SectionType;
  count: number;
  points_per_question?: number | null;
  difficulty_distribution?: Partial<Record<Difficulty, number>> | null;
  chapter_codes?: string[] | null;
}

export interface ExamTemplateInput {
  name: string;
  exam_type: ExamType;
  grade: number | null;
  version_label: string | null;
  duration_minutes: number | null;
  source: string | null;
  description: string | null;
  sections: TemplateSection[];
}

export interface ExamTemplate extends ExamTemplateInput {
  template_id: number;
  total_questions: number;
  status: TemplateStatus;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

const opts = { withCredentials: true };

/** Lỗi 422 nghiệp vụ của #5 → ApiError với message gồm các lý do. */
async function call<T>(send: () => Promise<{ data: T }>): Promise<T> {
  try {
    return (await send()).data;
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 422) {
      const detail = (e.response.data as { detail?: unknown })?.detail as { message?: string; errors?: string[] } | undefined;
      if (detail && !Array.isArray(detail) && typeof detail === 'object' && detail.errors) {
        throw new ApiError('TEMPLATE_INVALID', `${detail.message ?? 'Mẫu không hợp lệ'}: ${detail.errors.join('; ')}`, 422);
      }
    }
    throw toApiError(e);
  }
}

export const examTemplatesApi = {
  list: (params: { status?: TemplateStatus; exam_type?: ExamType; grade?: number }) =>
    request<ExamTemplate[]>(() => apiClient.get('/exam-templates', { ...opts, params })),
  get: (id: number) => request<ExamTemplate>(() => apiClient.get(`/exam-templates/${id}`, opts)),
  create: (input: ExamTemplateInput) => call<ExamTemplate>(() => apiClient.post('/exam-templates', input, opts)),
  update: (id: number, input: ExamTemplateInput) => call<ExamTemplate>(() => apiClient.put(`/exam-templates/${id}`, input, opts)),
  approve: (id: number) => call<ExamTemplate>(() => apiClient.post(`/exam-templates/${id}/approve`, null, opts)),
};
