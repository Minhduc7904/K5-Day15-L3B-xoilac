'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRealtimeSocket } from '@/features/realtime/realtime-connection';
import { NOTIFICATION_EVENT, notificationApi, type Notification } from './api';

type State = { items: Notification[]; unread: number; status: 'loading' | 'ready' | 'error' };

const KEEP = 50;

/**
 * Danh sách thông báo của học sinh. Tải khi mở, nhận thông báo mới qua Socket.IO, tải lại khi kết nối lại
 * hoặc khi tab hiện lại (lúc đó có thể đã lỡ sự kiện).
 */
export function useNotifications() {
  const socket = useRealtimeSocket();
  const [state, setState] = useState<State>({ items: [], unread: 0, status: 'loading' });

  const reload = useCallback(async () => {
    try {
      const page = await notificationApi.list();
      setState({ items: page.items, unread: page.unread, status: 'ready' });
    } catch {
      // Giữ danh sách cũ nếu đã có; chỉ báo lỗi khi chưa có gì để hiện.
      setState((prev) => (prev.status === 'ready' ? prev : { ...prev, status: 'error' }));
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') void reload();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [reload]);

  useEffect(() => {
    if (!socket) return;
    const onNew = (item: Notification) => {
      setState((prev) => {
        if (prev.items.some((existing) => existing.id === item.id)) return prev;
        return { status: 'ready', items: [item, ...prev.items].slice(0, KEEP), unread: prev.unread + (item.read_at ? 0 : 1) };
      });
    };
    const onConnect = () => void reload();
    socket.on(NOTIFICATION_EVENT, onNew);
    socket.on('connect', onConnect);
    return () => {
      socket.off(NOTIFICATION_EVENT, onNew);
      socket.off('connect', onConnect);
    };
  }, [socket, reload]);

  const markRead = useCallback(async (id: number) => {
    const now = new Date().toISOString();
    setState((prev) => {
      const target = prev.items.find((item) => item.id === id);
      if (!target || target.read_at) return prev;
      return { ...prev, unread: Math.max(0, prev.unread - 1), items: prev.items.map((item) => (item.id === id ? { ...item, read_at: now } : item)) };
    });
    try {
      await notificationApi.read(id);
    } catch {
      void reload();
    }
  }, [reload]);

  const markAll = useCallback(async () => {
    const now = new Date().toISOString();
    setState((prev) => ({ ...prev, unread: 0, items: prev.items.map((item) => (item.read_at ? item : { ...item, read_at: now })) }));
    try {
      await notificationApi.readAll();
    } catch {
      void reload();
    }
  }, [reload]);

  return { ...state, reload, markRead, markAll };
}
