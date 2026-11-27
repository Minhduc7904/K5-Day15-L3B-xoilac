/**
 * Client Socket.IO DUY NHẤT của app (#20). Chỉ useRealtime gọi các hàm ở đây.
 * Mỗi lần nối cần ticket mới (dùng một lần, 30 s), nên tắt tự nối lại của socket.io-client:
 * useRealtime tự xin ticket mới rồi gọi connectRealtime lại.
 */
import { io, type Socket } from 'socket.io-client';
import { socketUrl } from '@/lib/config';
import type { SessionRevokedEvent } from './types';

export interface RealtimeHandlers {
  onConnected: () => void;
  /** Server thu hồi phiên: đã nhận session:revoked, server sẽ ngắt ngay sau đó. */
  onRevoked: (event: SessionRevokedEvent) => void;
  /** Server từ chối lúc nối (connect_error), `code` theo docs/api/realtime-api.md. */
  onRefused: (code: string | undefined) => void;
  /** Mất kết nối ngoài ý muốn (mạng, ping timeout): nên xin ticket mới rồi nối lại. */
  onLost: () => void;
}

let socket: Socket | null = null;

export function connectRealtime(ticket: string, handlers: RealtimeHandlers): void {
  disconnectRealtime();
  const s = io(socketUrl || undefined, {
    path: '/api/socket.io',
    transports: ['websocket'],
    auth: { ticket },
    reconnection: false,
  });
  let revoked = false;
  s.on('connect', handlers.onConnected);
  s.on('session:revoked', (event: SessionRevokedEvent) => {
    revoked = true;
    handlers.onRevoked(event);
  });
  s.on('connect_error', (err: Error & { data?: { code?: string } }) => handlers.onRefused(err.data?.code));
  s.on('disconnect', (reason) => {
    // "io server disconnect": server chủ động ngắt (sau session:revoked). "io client disconnect": chính app ngắt.
    if (!revoked && reason !== 'io server disconnect' && reason !== 'io client disconnect') handlers.onLost();
  });
  socket = s;
}

export function disconnectRealtime(): void {
  if (!socket) return;
  socket.removeAllListeners();
  socket.disconnect();
  socket = null;
}
