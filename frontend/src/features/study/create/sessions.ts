'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { chapterOf, loadChapterCatalog } from '../chapters';
import {
  adaptDraft, chatAttachmentUrl, examChatApi, examChatError, type ServerDraft, type ServerPreview, type ServerSession, type Shortage,
} from '../exam-chat-api';
import { difficultyLabels } from '../labels';
import type { Exam, StructureProposal } from '../types';
import { rowsFromChapters, sameRows, type ExamPlan } from './plan';

export interface ChatMessage {
  id: string;
  role: 'student' | 'assistant';
  text: string;
  /** Ảnh vừa gửi là blob URL; ảnh đã lưu trên server là URL có xác thực. */
  images?: Array<{ url: string; name: string }>;
  proposal?: boolean;
  built?: { exam: Exam; shortages: string[] };
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  /** Đã có trên server. Đoạn chat mới chỉ nằm ở trình duyệt tới khi gửi tin đầu tiên. */
  persisted: boolean;
  /** Tin nhắn và bản xem trước đã tải từ server. */
  loaded: boolean;
  messages: ChatMessage[];
  proposal: StructureProposal | null;
  /** Kế hoạch tổng quan học sinh vừa chỉnh nhưng agent chưa phân bổ lại thành ma trận. */
  draft: ExamPlan | null;
  built: boolean;
  /** Bản xem trước gốc từ server (để biết version, đề xuất thiếu câu, mẫu kỳ thi). */
  preview: ServerPreview | null;
  serverDraft: ServerDraft | null;
  /** Học sinh đã chỉnh tên, thời gian hoặc ma trận ở trình duyệt mà chưa gửi lên server. */
  dirty: boolean;
}

export const uid = () => Math.random().toString(36).slice(2, 10);

export const newSession = (): ChatSession => {
  const now = new Date().toISOString();
  return {
    id: uid(), title: 'Đoạn chat mới', createdAt: now, updatedAt: now, persisted: false, loaded: true,
    messages: [], proposal: null, draft: null, built: false, preview: null, serverDraft: null, dirty: false,
  };
};

const fromServer = (item: ServerSession): ChatSession => ({
  ...newSession(), id: String(item.session_id), title: item.title, createdAt: item.created_at, updatedAt: item.updated_at,
  persisted: true, loaded: false,
});

export function shortageText(s: Shortage) {
  const where = s.chapter ? chapterOf(s.chapter).name : s.section_order ? `Phần ${s.section_order}` : 'Đề';
  return `${where}${s.difficulty ? ` · ${difficultyLabels[s.difficulty]}` : ''}: thiếu ${Math.max(0, s.requested - s.available)} câu`;
}

/** Bản xem trước theo chương → hàng đề xuất của giao diện. Mẫu kỳ thi và bản đã huỷ không có. */
export function toProposal(preview: ServerPreview | null): StructureProposal | null {
  if (!preview || preview.status === 'CANCELLED' || preview.structure.kind !== 'CHAPTER') return null;
  const s = preview.structure;
  const rows = s.rows?.length ? s.rows : rowsFromChapters(s.chapters, s.difficulty_weights);
  return { title: s.title || 'Đề ôn tập', reason: preview.reason ?? '', durationMinutes: s.duration_minutes ?? 0, rows };
}

export function builtCard(draft: ServerDraft): NonNullable<ChatMessage['built']> {
  return { exam: adaptDraft(draft).exam, shortages: draft.shortages.map(shortageText) };
}

/**
 * Các đoạn chat tạo đề, lưu ở backend. Đoạn chat mới chỉ tồn tại ở trình duyệt tới khi gửi tin đầu tiên.
 * Chỉnh sửa trên bảng cấu trúc (tên đề, thời gian, ma trận) giữ ở trình duyệt, gửi lên server trước khi nhắn hoặc dựng đề.
 */
export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const ref = useRef<ChatSession[]>([]);

  useEffect(() => {
    ref.current = sessions;
  }, [sessions]);

  const update = useCallback((id: string, fn: (s: ChatSession) => ChatSession) => {
    setSessions((list) => list.map((s) => (s.id === id ? fn(s) : s)));
  }, []);

  const loadState = useCallback(async (id: string, keepDraft = false) => {
    const state = await examChatApi.state(Number(id));
    const sid = state.session.session_id;
    const built = state.preview?.status === 'BUILT' && state.draft ? builtCard(state.draft) : null;
    const lastAssistant = state.messages.findLast((m) => m.role === 'assistant')?.message_id;
    update(id, (s) => ({
      ...s,
      loaded: true,
      messages: state.messages.map((m) => ({
        id: String(m.message_id),
        role: m.role,
        text: m.content,
        images: m.attachments.map((a) => ({ url: chatAttachmentUrl(sid, a.attachment_id), name: `Ảnh ${a.position}` })),
        proposal: m.role === 'assistant' && m.preview_version != null,
        built: built && m.message_id === lastAssistant ? built : undefined,
      })),
      preview: state.preview,
      serverDraft: state.draft,
      proposal: toProposal(state.preview),
      built: state.preview?.status === 'BUILT',
      dirty: false,
      draft: keepDraft ? s.draft : null,
    }));
  }, [update]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [saved] = await Promise.all([
        examChatApi.sessions().catch((cause) => {
          setError(examChatError(cause));
          return [] as ServerSession[];
        }),
        loadChapterCatalog(),
      ]);
      if (!alive) return;
      const fresh = newSession();
      const wanted = new URLSearchParams(window.location.search).get('session');
      setSessions([fresh, ...saved.map(fromServer)]);
      setActiveId(wanted && saved.some((s) => String(s.session_id) === wanted) ? wanted : fresh.id);
      setReady(true);
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Mở đoạn chat đã lưu mà chưa tải nội dung (từ danh sách, hoặc từ ?session=).
  useEffect(() => {
    const s = ref.current.find((x) => x.id === activeId);
    if (ready && s && s.persisted && !s.loaded) {
      loadState(activeId).catch((cause) => setError(examChatError(cause)));
    }
  }, [ready, activeId, sessions, loadState]);

  const select = useCallback((id: string) => {
    setActiveId(id);
    const s = ref.current.find((x) => x.id === id);
    window.history.replaceState(null, '', s?.persisted ? `/exams/new?session=${id}` : '/exams/new');
  }, []);

  /** Mở đoạn chat trống. Đã có một đoạn trống thì dùng lại, không tạo thêm. */
  const create = useCallback(() => {
    const empty = ref.current.find((s) => !s.persisted);
    if (empty) {
      select(empty.id);
      return empty.id;
    }
    const fresh = newSession();
    setSessions((list) => [fresh, ...list]);
    setActiveId(fresh.id);
    window.history.replaceState(null, '', '/exams/new');
    return fresh.id;
  }, [select]);

  /** Tin nhắn đầu tiên: tạo phiên trên server rồi đổi mã đoạn chat cục bộ thành mã server. */
  const promote = useCallback(async (localId: string) => {
    const created = await examChatApi.create();
    const id = String(created.session_id);
    update(localId, (s) => ({ ...s, id, persisted: true, loaded: true, createdAt: created.created_at, updatedAt: created.updated_at }));
    setActiveId(id);
    window.history.replaceState(null, '', `/exams/new?session=${id}`);
    return id;
  }, [update]);

  const refreshList = useCallback(async () => {
    const saved = await examChatApi.sessions();
    setSessions((list) => {
      const known = new Map(list.map((s) => [s.id, s]));
      const server = saved.map((item) => {
        const old = known.get(String(item.session_id));
        return old ? { ...old, title: item.title, updatedAt: item.updated_at } : fromServer(item);
      });
      return [...list.filter((s) => !s.persisted), ...server];
    });
  }, []);

  /** Gửi các chỉnh sửa chưa lưu lên server. Trả bản xem trước mới nhất (hoặc `null` khi chưa có). */
  const flush = useCallback(async (id: string, override?: StructureProposal): Promise<ServerPreview | null> => {
    const s = ref.current.find((x) => x.id === id);
    if (!s || !s.preview) return s?.preview ?? null;
    const next = override ?? s.proposal;
    const base = toProposal(s.preview);
    if (!next || !base || (!override && !s.dirty)) return s.preview;
    const edit: Parameters<typeof examChatApi.edit>[2] = {};
    if (!sameRows(base.rows, next.rows)) edit.rows = next.rows;
    if (base.durationMinutes !== next.durationMinutes) edit.duration_minutes = next.durationMinutes;
    const title = next.title.trim();
    if (title && title !== base.title) edit.title = title;
    if (!Object.keys(edit).length) {
      update(id, (x) => ({ ...x, dirty: false }));
      return s.preview;
    }
    const preview = await examChatApi.edit(Number(id), s.preview.version, edit);
    update(id, (x) => ({ ...x, preview, proposal: toProposal(preview), built: false, dirty: false, draft: override ? null : x.draft }));
    return preview;
  }, [update]);

  const rename = useCallback(async (id: string, title: string) => {
    const clean = title.trim();
    if (!clean) return;
    const s = ref.current.find((x) => x.id === id);
    const saved = s?.persisted ? (await examChatApi.renameSession(Number(id), clean)).title : clean;
    update(id, (x) => ({ ...x, title: saved ?? clean }));
  }, [update]);

  const remove = useCallback(async (id: string) => {
    const s = ref.current.find((x) => x.id === id);
    if (s?.persisted) await examChatApi.deleteSession(Number(id));
    const rest = ref.current.filter((x) => x.id !== id);
    const empty = rest.find((x) => !x.persisted) ?? newSession();
    setSessions(rest.some((x) => x.id === empty.id) ? rest : [empty, ...rest]);
    if (activeId === id) {
      setActiveId(empty.id);
      window.history.replaceState(null, '', '/exams/new');
    }
  }, [activeId]);

  const active = sessions.find((s) => s.id === activeId) ?? null;
  return { sessions, active, activeId, ready, error, select, create, update, rename, remove, loadState, promote, refreshList, flush };
}

/** Nhóm theo thời gian cập nhật gần nhất, mới nhất trước. */
export function groupSessions(sessions: ChatSession[]) {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const today = startOfToday.getTime();
  const day = 86_400_000;
  const groups: Array<{ label: string; items: ChatSession[] }> = [
    { label: 'Hôm nay', items: [] },
    { label: 'Hôm qua', items: [] },
    { label: '7 ngày qua', items: [] },
    { label: 'Cũ hơn', items: [] },
  ];
  for (const s of [...sessions].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))) {
    const t = Date.parse(s.updatedAt);
    const g = t >= today ? 0 : t >= today - day ? 1 : t >= today - 7 * day ? 2 : 3;
    groups[g].items.push(s);
  }
  return groups.filter((g) => g.items.length);
}
