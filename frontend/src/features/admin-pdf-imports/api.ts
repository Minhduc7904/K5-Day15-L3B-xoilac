/**
 * Lớp gọi API nhập đề PDF của #3 (/api/v1/admin/pdf-imports) cho trang duyệt của admin (#11).
 * Chỉ dùng API đã có; hợp đồng ở docs/ai/pdf-import/api.md.
 */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';

export type ImportStatus = 'queued' | 'processing' | 'ready_for_review' | 'failed';
export type DraftStatus = 'pending' | 'approved' | 'rejected';

export interface PdfImport {
  id: number;
  filename: string;
  status: ImportStatus;
  stage: string;
  pageCount: number | null;
  originalMediaId: number;
  error: string | null;
  warnings: string[] | null;
  ocrModel: string | null;
  extractionModel: string | null;
  createdAt: string;
  statusUrl: string;
  draftCount?: number;
}

export interface DraftStatement {
  content: string;
  isCorrect: boolean | null;
}

export interface Suggestions {
  chapter: string | null;
  subchapter: string | null;
  grade: number | null;
  difficulty: string | null;
  neighbors: Array<{ questionId: number; chapter: string; subchapter: string | null; difficulty: string; similarity: number }>;
}

export interface PdfDraft {
  id: number;
  position: number;
  status: DraftStatus;
  questionId: number | null;
  section: string;
  number: string;
  sourcePages: number[];
  type: 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'TRUE_FALSE' | 'SHORT_ANSWER' | 'ESSAY';
  content: string;
  statements: DraftStatement[];
  correctAnswer: string | null;
  solution: string | null;
  solutionPages?: number[];
  answerState: string;
  flags: string[];
  imageDependent: boolean;
  imageReviewed: boolean;
  chapterCodes: string[];
  difficulty: 'NB' | 'TH' | 'VD' | 'VDC' | null;
  suggestions: Suggestions | null;
}

export type DraftEdit = Partial<Pick<PdfDraft, 'content' | 'statements' | 'correctAnswer' | 'solution' | 'chapterCodes' | 'difficulty' | 'imageReviewed'>>;

const opts = { withCredentials: true };
const base = '/admin/pdf-imports';

export const pdfImportsApi = {
  list: (offset = 0, limit = 25) => request<PdfImport[]>(() => apiClient.get(base, { ...opts, params: { offset, limit } })),
  get: (id: number) => request<PdfImport>(() => apiClient.get(`${base}/${id}`, opts)),
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<PdfImport>(() => apiClient.post(base, form, { ...opts, timeout: 120_000 }));
  },
  drafts: (id: number) => request<PdfDraft[]>(() => apiClient.get(`${base}/${id}/drafts`, opts)),
  edit: (id: number, draftId: number, edit: DraftEdit) =>
    request<PdfDraft>(() => apiClient.patch(`${base}/${id}/drafts/${draftId}`, edit, opts)),
  approve: (id: number, draftId: number) => request<PdfDraft>(() => apiClient.post(`${base}/${id}/drafts/${draftId}/approve`, null, opts)),
  reject: (id: number, draftId: number) => request<PdfDraft>(() => apiClient.post(`${base}/${id}/drafts/${draftId}/reject`, null, opts)),
  /** URL có ký, hết hạn sau 5 phút; trả đường dẫn tuyệt đối theo path (đã gồm /api/v1). */
  mediaUrl: (id: number, mediaId: number) =>
    request<{ url: string; expiresAt: number }>(() => apiClient.get(`${base}/${id}/media/${mediaId}/url`, opts)),
};

export const IMPORT_STATUS: Record<ImportStatus, { label: string; tone: 'info' | 'warning' | 'success' | 'danger' }> = {
  queued: { label: 'Đang chờ', tone: 'info' },
  processing: { label: 'Đang xử lý', tone: 'warning' },
  ready_for_review: { label: 'Chờ duyệt', tone: 'success' },
  failed: { label: 'Lỗi', tone: 'danger' },
};

export const DRAFT_STATUS: Record<DraftStatus, { label: string; tone: 'neutral' | 'success' | 'danger' }> = {
  pending: { label: 'Chờ duyệt', tone: 'neutral' },
  approved: { label: 'Đã duyệt', tone: 'success' },
  rejected: { label: 'Đã bỏ', tone: 'danger' },
};

export const FLAG_LABELS: Record<string, string> = {
  solution_review: 'Cần kiểm lời giải',
  image_review: 'Cần kiểm hình',
  image_source_mismatch: 'Hình không khớp trang nguồn',
  image_missing: 'Thiếu hình',
  image_unplaced: 'Có hình chưa đặt vào câu',
  label_review: 'Cần gắn nhãn tay',
};
