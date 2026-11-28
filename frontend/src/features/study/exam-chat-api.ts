import { isAxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { apiBaseUrl } from '@/lib/config';
import { notFoundError } from './errors';
import type { Difficulty, Exam, ExamSummary, PublicQuestion, QuestionType, StructureRow } from './types';

export interface ServerSession {
  session_id: number;
  created_at: string;
  updated_at: string;
  title: string;
}
export interface ServerMessage {
  message_id: number;
  role: 'student' | 'assistant';
  content: string;
  preview_version: number | null;
  attachments: Array<{ attachment_id: number; position: number; mime_type: string }>;
}
export interface Shortage {
  chapter: string | null;
  difficulty: Difficulty | null;
  requested: number;
  available: number;
  section_order?: number | null;
  question_type?: string | null;
}
interface TemplateSection {
  order: number;
  title: string;
  question_type: QuestionType;
  count: number;
  difficulty_distribution: Partial<Record<Difficulty, number>> | null;
  allowed_chapters: string[] | null;
  chapters: string[] | null;
}
export const defaultPointWeights = { SINGLE_CHOICE: 30, TRUE_FALSE: 40, SHORT_ANSWER: 30 };
export type PointWeights = typeof defaultPointWeights;

type Structure = {
  duration_minutes: number | null;
} & ({
  kind: 'CHAPTER';
  chapters: Array<{ code: string; count: number }>;
  rows: StructureRow[] | null;
  difficulty_weights: Partial<Record<Difficulty, number>>;
  type_point_weights?: PointWeights;
} | {
  kind: 'EXAM_TEMPLATE';
  template_name: string;
  sections: TemplateSection[];
  source: string | null;
});
export interface ServerPreview {
  version: number;
  status: 'PROPOSED' | 'EDITED' | 'CONFIRMED' | 'BUILT';
  structure: Structure;
  offer: { requested: number; count: number; shortages: Shortage[] } | null;
  operation: { kind: string; positions: number[] } | null;
}
export interface ServerDraft {
  draft_id: number;
  session_id: number;
  title: string;
  created_at: string;
  structure: Structure;
  shortages: Shortage[];
  items: Array<{
    code: string;
    order: number;
    chapter: string | null;
    difficulty: Difficulty | null;
    type: QuestionType;
    section_order: number | null;
    section_title: string | null;
    points?: number | null;
    max_points?: number | null;
    content: string;
    statements: Array<{ order: number | null; content: string }>;
  }>;
}
interface State {
  session: ServerSession;
  messages: ServerMessage[];
  preview: ServerPreview | null;
  draft: ServerDraft | null;
}
export type ExamChatEvent =
  | { event: 'message'; data: { delta: string } }
  | { event: 'preview'; data: ServerPreview | null }
  | { event: 'draft'; data: ServerDraft }
  | { event: 'done'; data: unknown }
  | { event: 'error'; data: { message: string } };

const root = '/exam-chat';
const sessionPath = (id: number) => root + '/sessions/' + id;
const typeTitles: Record<QuestionType, string> = {
  SINGLE_CHOICE: 'Trắc nghiệm', TRUE_FALSE: 'Đúng sai', SHORT_ANSWER: 'Trả lời ngắn',
  MULTIPLE_CHOICE: 'Nhiều đáp án', ESSAY: 'Tự luận',
};

export function examChatError(error: unknown) {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail?.errors)) return detail.errors.join(' ');
    if (typeof detail?.message === 'string') return detail.message;
    if (typeof detail === 'string') return detail;
  }
  return error instanceof Error ? error.message : 'Không thể xử lý yêu cầu. Bạn thử lại nhé.';
}

export const chatAttachmentUrl = (session: number, attachment: number) =>
  apiBaseUrl + sessionPath(session) + '/attachments/' + attachment;

export const draftLink = (draft: ServerDraft) => '/exams/draft-' + draft.draft_id;

export const examChatApi = {
  async sessions(signal?: AbortSignal) {
    return (await apiClient.get<ServerSession[]>(root + '/sessions', { signal })).data;
  },
  async create() {
    return (await apiClient.post<ServerSession>(root + '/sessions', {})).data;
  },
  async state(id: number) {
    return (await apiClient.get<State>(sessionPath(id))).data;
  },
  async transcript(id: number, before?: number) {
    return (await apiClient.get<ServerMessage[]>(sessionPath(id) + '/transcript', { params: { before } })).data;
  },
  async chapters(signal?: AbortSignal) {
    return (await apiClient.get<Record<string, { name: string; parent_code: string | null; grade?: number | null }>>(root + '/chapters', { signal })).data;
  },
  async edit(id: number, version: number, edit: { rows?: StructureRow[]; chapter_codes?: string[]; duration_minutes?: number; type_point_weights?: PointWeights }) {
    return (await apiClient.patch<ServerPreview>(sessionPath(id) + '/preview', { version, edit })).data;
  },
  async confirm(id: number, version: number, acceptedCount?: number) {
    return (await apiClient.post<{ preview: ServerPreview; draft: ServerDraft | null; message: string }>(
      sessionPath(id) + '/preview/confirm', { version, accepted_count: acceptedCount }, { timeout: 30000 },
    )).data;
  },
  async *send(id: number, text: string, version: number, images: File[] = []): AsyncGenerator<ExamChatEvent> {
    const path = apiBaseUrl + sessionPath(id) + '/messages';
    const headers = new Headers({ Accept: 'text/event-stream' });
    let body: FormData | string;
    if (images.length) {
      body = new FormData();
      body.append('text', text);
      body.append('version', String(version));
      for (const image of images) body.append('images', image);
    } else {
      headers.set('Content-Type', 'application/json');
      body = JSON.stringify({ text, version });
    }
    const response = await fetch(path + (images.length ? '/with-images' : ''), {
      method: 'POST', credentials: 'same-origin', headers, body, signal: AbortSignal.timeout(110000),
    });
    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail?.message ?? (response.status === 401
        ? 'Phiên đăng nhập đã hết. Bạn hãy đăng nhập lại.' : 'Không gửi được tin nhắn. Bạn thử lại nhé.'));
    }
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = '';
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer = (buffer + value).replace(/\r\n/g, '\n');
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          const event = frame.split('\n').find((line) => line.startsWith('event:'))?.slice(6).trim();
          const data = frame.split('\n').filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n');
          if (event && data) {
            yield { event, data: JSON.parse(data) } as ExamChatEvent;
            if (event === 'done' || event === 'error') return;
          }
        }
      }
      throw new Error('Kết nối chat bị ngắt.');
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  },
  async drafts() {
    return (await apiClient.get<ServerDraft[]>(root + '/drafts')).data;
  },
  async draft(id: string) {
    try {
      return (await apiClient.get<ServerDraft>(root + '/drafts/' + id)).data;
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 404) throw notFoundError('Không tìm thấy đề.');
      throw error;
    }
  },
};

export function adaptDraft(draft: ServerDraft): { exam: Exam; questions: PublicQuestion[]; attempts: [] } {
  const sections = new Map<string, Exam['sections'][number]>();
  for (const item of draft.items) {
    const id = String(item.section_order ?? item.type);
    const section = sections.get(id) ?? { id, title: item.section_title ?? typeTitles[item.type], type: item.type, questionIds: [] };
    section.questionIds.push(item.code);
    sections.set(id, section);
  }
  return {
    exam: {
      id: 'draft-' + draft.draft_id, title: draft.title, source: 'ai',
      createdAt: draft.created_at, durationMinutes: draft.structure.duration_minutes ?? 0,
      chapters: [...new Set(draft.items.flatMap((item) => item.chapter ? [item.chapter] : []))],
      sections: [...sections.values()],
    },
    questions: draft.items.map((item) => ({
      id: item.code, type: item.type, chapter: item.chapter ?? '', order: item.order,
      difficulty: item.difficulty ?? 'NB', difficultyKnown: item.difficulty !== null,
      maxPoints: item.max_points ?? item.points ?? undefined,
      content: item.content, remoteDraftId: draft.draft_id,
      statements: item.statements.map((option, index) => ({
        label: String.fromCharCode((item.type === 'TRUE_FALSE' ? 97 : 65) + index), content: option.content,
      })),
    })),
    attempts: [],
  };
}

export function draftSummary(draft: ServerDraft): ExamSummary {
  return { ...adaptDraft(draft).exam, questionCount: draft.items.length, attempts: 0, bestScore: null, lastAttemptAt: null };
}
