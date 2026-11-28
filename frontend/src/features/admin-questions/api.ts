/**
 * Lớp gọi API ngân hàng câu hỏi cho admin (#11): /api/v1/admin/questions. Mọi màn của feature chỉ gọi qua đây.
 * Lỗi mất phiên do interceptor của lib/api-client xử lý chung. Xem docs/api/admin-data-api.md.
 */
import { apiClient } from '@/lib/api-client';
import { apiBaseUrl } from '@/lib/config';
import { request } from '@/lib/api-error';
import type { QuestionDetail, QuestionInput, QuestionList, QuestionQuery } from './types';

const opts = { withCredentials: true };

const FIELD_MESSAGES: Record<string, string> = {
  content: 'Nội dung không được để trống (tối đa 20.000 ký tự).',
  chapter_ids: 'Chọn ít nhất một chương (tối đa 10).',
  statements: 'Tối đa 12 lựa chọn.',
};

/** Đường dẫn ảnh `media:ID` cho admin (cookie phiên đi kèm vì cùng origin qua rewrites). */
export const questionMediaUrl = (id: string | number) => `${apiBaseUrl}/admin/questions/media/${encodeURIComponent(String(id))}`;

export const adminQuestionsApi = {
  list: (query: QuestionQuery) =>
    request<QuestionList>(() => apiClient.get('/admin/questions', { ...opts, params: { ...query, q: query.q || undefined } })),
  get: (id: number) => request<QuestionDetail>(() => apiClient.get(`/admin/questions/${id}`, opts)),
  create: (input: QuestionInput) => request<QuestionDetail>(() => apiClient.post('/admin/questions', input, opts), FIELD_MESSAGES),
  update: (id: number, input: QuestionInput) =>
    request<QuestionDetail>(() => apiClient.put(`/admin/questions/${id}`, input, opts), FIELD_MESSAGES),
  archive: (id: number) => request<QuestionDetail>(() => apiClient.post(`/admin/questions/${id}/archive`, null, opts)),
  restore: (id: number) => request<QuestionDetail>(() => apiClient.post(`/admin/questions/${id}/restore`, null, opts)),
  uploadImage: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ media_id: number; url: string }>(() =>
      apiClient.post('/admin/questions/media', form, { ...opts, timeout: 30_000 }),
    );
  },
};
