'use client';

import { useEffect, useSyncExternalStore } from 'react';
import { io, type Socket } from 'socket.io-client';
import { signedOut } from '@/features/auth/auth-slice';
import { apiClient } from '@/lib/api-client';
import { mockMode } from '@/lib/config';
import { useAppDispatch, useAppSelector } from '@/store';

const socketOrigin = process.env.NEXT_PUBLIC_SOCKET_URL
  || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : undefined);

let currentSocket: Socket | null = null;
const subscribers = new Set<() => void>();

function subscribe(listener: () => void) {
  subscribers.add(listener);
  return () => { subscribers.delete(listener); };
}

function publishSocket(socket: Socket | null) {
  currentSocket = socket;
  subscribers.forEach((listener) => listener());
}

export function useRealtimeSocket() {
  return useSyncExternalStore(subscribe, () => currentSocket, () => null);
}

async function requestTicket(signal: AbortSignal) {
  const { data } = await apiClient.post<{ ticket: string }>('/auth/socket-ticket', undefined, { signal });
  return data.ticket;
}

export function RealtimeConnection() {
  const userId = useAppSelector((state) => state.auth.user?.user_id);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (mockMode || userId == null || !socketOrigin) return;

    const socket = io(socketOrigin, {
      path: '/api/socket.io',
      transports: ['websocket'],
      autoConnect: false,
      reconnection: false,
      timeout: 10_000,
    });
    const lifetime = new AbortController();
    let failures = 0;
    let retry: number | undefined;

    function scheduleReconnect() {
      if (lifetime.signal.aborted || retry !== undefined) return;
      const delay = Math.min(30_000, 1_000 * 2 ** Math.min(failures++, 5));
      retry = window.setTimeout(() => {
        retry = undefined;
        void connect();
      }, delay);
    }

    async function connect() {
      try {
        const ticket = await requestTicket(lifetime.signal);
        if (lifetime.signal.aborted) return;
        socket.auth = { ticket };
        socket.connect();
      } catch {
        scheduleReconnect();
      }
    }

    socket.on('connect', () => {
      failures = 0;
      socket.auth = {};
    });
    socket.on('connect_error', scheduleReconnect);
    socket.on('disconnect', scheduleReconnect);
    socket.on('session:revoked', () => dispatch(signedOut('session-expired')));
    publishSocket(socket);
    void connect();

    return () => {
      lifetime.abort();
      window.clearTimeout(retry);
      socket.removeAllListeners();
      socket.disconnect();
      if (currentSocket === socket) publishSocket(null);
    };
  }, [dispatch, userId]);

  return null;
}
