'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Exam, StructureProposal } from '../types';
import type { ExamPlan } from './plan';

export interface ChatMessage {
  id: string;
  role: 'student' | 'assistant';
  text: string;
  /** `url` rỗng khi tải lại trang: ảnh blob không lưu được, chỉ giữ tên. */
  images?: Array<{ url: string; name: string }>;
  proposal?: boolean;
  built?: { exam: Exam; shortages: string[] };
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  proposal: StructureProposal | null;
  /** Kế hoạch tổng quan học sinh vừa chỉnh nhưng agent chưa phân bổ lại thành ma trận. */
  draft: ExamPlan | null;
  built: boolean;
}

/**
 * Lưu các đoạn chat tạo đề trên máy (localStorage) cho bản mock.
 * Khi backend có API phiên chat (#4), thay phần đọc/ghi ở đây, giữ nguyên hook.
 */
const STORAGE_KEY = 'examind:chat-sessions:v1';
export const uid = () => Math.random().toString(36).slice(2, 10);

export const newSession = (): ChatSession => {
  const now = new Date().toISOString();
  return { id: uid(), title: 'Đoạn chat mới', createdAt: now, updatedAt: now, messages: [], proposal: null, draft: null, built: false };
};

function read(): ChatSession[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ChatSession[]) : [];
  } catch {
    return [];
  }
}

function write(sessions: ChatSession[]) {
  try {
    const stored = sessions
      .filter((s) => s.messages.length > 0)
      .map((s) => ({ ...s, messages: s.messages.map((m) => (m.images ? { ...m, images: m.images.map((i) => ({ name: i.name, url: '' })) } : m)) }));
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Hết dung lượng hoặc chế độ riêng tư: vẫn dùng được trong phiên hiện tại.
  }
}

export function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = read();
    const fresh = newSession();
    // Đọc localStorage chỉ có ở client, nên nạp sau khi mount để HTML lúc hydrate khớp với server.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessions([fresh, ...stored]);
    setActiveId(fresh.id);
    setReady(true);
  }, []);

  useEffect(() => {
    // Chỉ ghi sau khi đã nạp, nếu không lần render đầu (danh sách rỗng) sẽ xoá dữ liệu đã lưu.
    if (ready) write(sessions);
  }, [ready, sessions]);

  const update = useCallback((id: string, fn: (s: ChatSession) => ChatSession) => {
    setSessions((list) => list.map((s) => (s.id === id ? fn(s) : s)));
  }, []);

  /** Mở đoạn chat trống. Đã có một đoạn trống thì dùng lại, không tạo thêm. */
  const create = useCallback(() => {
    const empty = sessions.find((s) => s.messages.length === 0);
    if (empty) {
      setActiveId(empty.id);
      return empty.id;
    }
    const fresh = newSession();
    setSessions((list) => [fresh, ...list]);
    setActiveId(fresh.id);
    return fresh.id;
  }, [sessions]);

  const rename = useCallback((id: string, title: string) => update(id, (s) => ({ ...s, title: title.trim() || s.title })), [update]);

  const remove = useCallback(
    (id: string) => {
      const rest = sessions.filter((s) => s.id !== id);
      if (rest.length === 0) {
        const fresh = newSession();
        setSessions([fresh]);
        setActiveId(fresh.id);
        return;
      }
      setSessions(rest);
      if (activeId === id) setActiveId(rest[0].id);
    },
    [sessions, activeId],
  );

  const active = sessions.find((s) => s.id === activeId) ?? null;
  return { sessions, active, activeId, select: setActiveId, create, update, rename, remove };
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
