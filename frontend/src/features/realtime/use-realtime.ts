'use client';

/**
 * Giữ kết nối Socket.IO theo trạng thái đăng nhập (#20). Gắn MỘT lần ở AppProvider qua <RealtimeBridge />.
 * - Đã đăng nhập: xin ticket qua realtimeApi rồi nối. Mất mạng: xin ticket mới, nối lại (lùi dần tới 30 s).
 * - Đăng xuất (user rời store): ngắt.
 * - Nhận session:revoked, hoặc bị từ chối vì phiên đã mất: ngắt, xoá user khỏi store, về /login.
 * Chế độ mock: không nối (không có server socket).
 */
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useToast } from '@/components/ui/toast';
import { signedOut } from '@/features/auth/auth-slice';
import { isSessionLost } from '@/lib/api-error';
import { mockMode } from '@/lib/config';
import { useAppDispatch, useAppSelector } from '@/store';
import { realtimeApi } from './api';
import { connectRealtime, disconnectRealtime } from './client';
import { realtimeStatusChanged } from './realtime-slice';
import { REVOKE_MESSAGES, type RevokeReason } from './types';

const SESSION_CODES = new Set(['SESSION_MISSING', 'SESSION_INVALID', 'SESSION_EXPIRED', 'SESSION_REVOKED', 'ACCOUNT_DISABLED']);
const MAX_BACKOFF_MS = 30_000;

export function useRealtime() {
  const status = useAppSelector((s) => s.auth.status);
  const userId = useAppSelector((s) => s.auth.user?.user_id);
  const dispatch = useAppDispatch();
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    if (mockMode) {
      dispatch(realtimeStatusChanged(status === 'authenticated' ? 'mock' : 'idle'));
      return;
    }
    if (status !== 'authenticated') {
      disconnectRealtime();
      dispatch(realtimeStatusChanged('idle'));
      return;
    }

    let cancelled = false;
    let retry: number | undefined;

    const signOut = (reason: RevokeReason | null) => {
      cancelled = true;
      disconnectRealtime();
      dispatch(realtimeStatusChanged('idle'));
      dispatch(signedOut());
      // Đăng xuất ở chính tab này đã có thông báo riêng; các lý do khác thì báo cho người dùng biết vì sao.
      if (reason && reason !== 'logout') toast({ tone: 'warning', title: 'Phiên đã kết thúc', description: REVOKE_MESSAGES[reason] });
      router.replace('/login');
    };

    const scheduleRetry = (attempt: number) => {
      if (cancelled) return;
      dispatch(realtimeStatusChanged('reconnecting'));
      retry = window.setTimeout(() => void open(attempt + 1), Math.min(1000 * 2 ** attempt, MAX_BACKOFF_MS));
    };

    const open = async (attempt: number) => {
      if (cancelled) return;
      dispatch(realtimeStatusChanged(attempt === 0 ? 'connecting' : 'reconnecting'));
      let ticket: string;
      try {
        ticket = (await realtimeApi.socketTicket()).ticket;
      } catch (error) {
        if (isSessionLost(error)) signOut('expired');
        else scheduleRetry(attempt);
        return;
      }
      if (cancelled) return;
      connectRealtime(ticket, {
        onConnected: () => dispatch(realtimeStatusChanged('connected')),
        onRevoked: ({ reason }) => signOut(reason),
        onRefused: (code) => (code && SESSION_CODES.has(code) ? signOut('expired') : scheduleRetry(attempt)),
        onLost: () => scheduleRetry(0),
      });
    };

    void open(0);
    return () => {
      cancelled = true;
      window.clearTimeout(retry);
      disconnectRealtime();
    };
  }, [status, userId, dispatch, router, toast]);
}

/** Đặt một lần trong cây Provider để useRealtime chạy suốt vòng đời app. */
export function RealtimeBridge() {
  useRealtime();
  return null;
}
