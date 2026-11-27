/**
 * Trạng thái tạm của luồng quên mật khẩu: email đã nhập và reset token sau khi xác minh OTP.
 * Lưu ở sessionStorage của tab, không đưa email lên URL.
 */
const KEY = 'examind:reset-flow';

export interface ResetFlow {
  email: string;
  sentAt: number;
  resetToken?: string;
}

export function readResetFlow(): ResetFlow | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as ResetFlow) : null;
  } catch {
    return null;
  }
}

export function writeResetFlow(flow: ResetFlow) {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(flow));
  } catch {
    /* bỏ qua */
  }
}

export function clearResetFlow() {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* bỏ qua */
  }
}
