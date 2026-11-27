/** Khớp docs/api/realtime-api.md (#20). */
export type RevokeReason = 'logout' | 'disabled' | 'password_reset' | 'role_changed' | 'expired';

export interface SessionRevokedEvent {
  reason: RevokeReason;
}

export interface SocketTicket {
  ticket: string;
  expires_in: number;
}

/** `mock`: chế độ mock không có server socket nên không nối. */
export type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'mock';

export const REVOKE_MESSAGES: Record<RevokeReason, string> = {
  logout: 'Bạn đã đăng xuất.',
  disabled: 'Tài khoản của bạn đã bị khoá.',
  password_reset: 'Mật khẩu của bạn vừa được đặt lại. Hãy đăng nhập lại.',
  role_changed: 'Quyền của tài khoản vừa thay đổi. Hãy đăng nhập lại.',
  expired: 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.',
};
