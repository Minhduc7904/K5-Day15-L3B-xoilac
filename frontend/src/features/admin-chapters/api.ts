/**
 * Lớp gọi API danh mục chương cho admin (#11): /api/v1/admin/chapters. Xem docs/api/admin-data-api.md.
 * Feature câu hỏi dùng `adminChaptersApi.tree` cho ô chọn chương.
 */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';

export interface ChapterNode {
  chapter_id: number;
  code: string | null;
  name: string;
  slug: string | null;
  parent_chapter_id: number | null;
  order_in_parent: number | null;
  level: number;
  grade: number | null;
  question_count: number;
  subtree_question_count: number;
  children: ChapterNode[];
}

export interface ChapterInput {
  name: string;
  code: string;
  slug?: string | null;
  parent_chapter_id: number | null;
  order_in_parent?: number | null;
}

const opts = { withCredentials: true };
const FIELD_MESSAGES: Record<string, string> = {
  name: 'Tên chương từ 1 đến 191 ký tự.',
  code: 'Mã chương từ 3 đến 191 ký tự.',
  slug: 'Slug tối đa 191 ký tự.',
};

export const adminChaptersApi = {
  tree: (grade?: number) =>
    request<ChapterNode[]>(() => apiClient.get('/admin/chapters', { ...opts, params: grade ? { grade } : undefined })),
  create: (input: ChapterInput) => request<ChapterNode>(() => apiClient.post('/admin/chapters', input, opts), FIELD_MESSAGES),
  update: (id: number, input: ChapterInput) =>
    request<ChapterNode>(() => apiClient.put(`/admin/chapters/${id}`, input, opts), FIELD_MESSAGES),
  remove: (id: number) => request<void>(() => apiClient.delete(`/admin/chapters/${id}`, opts)),
};

/** Duyệt cây theo thứ tự hiển thị, trả danh sách phẳng kèm độ sâu (cho ô chọn có thụt lề). */
export function flattenTree(nodes: ChapterNode[], depth = 0): Array<{ node: ChapterNode; depth: number }> {
  return nodes.flatMap((node) => [{ node, depth }, ...flattenTree(node.children, depth + 1)]);
}

export const chapterLabel = (c: { code: string | null; name: string }) => (c.code ? `${c.code} · ${c.name}` : c.name);
