import axios, { isAxiosError } from 'axios';
import { apiBaseUrl } from './config';

export const apiClient = axios.create({ baseURL: apiBaseUrl, timeout: 5000 });

/** Mã lỗi nghĩa là phiên không còn dùng được (docs/api/auth-api.md). REAUTH_FAILED, FORBIDDEN_ROLE không thuộc nhóm này. */
const SESSION_LOST = new Set(['SESSION_MISSING', 'SESSION_INVALID', 'SESSION_EXPIRED', 'SESSION_REVOKED', 'ACCOUNT_DISABLED']);
/** Các lời gọi tự xử lý lỗi phiên: kiểm phiên lúc khởi động, đăng nhập, đăng xuất. */
const SELF_HANDLED = ['/auth/me', '/auth/login', '/auth/logout'];

let sessionLostHandler: (() => void) | null = null;

/** Đăng ký hàm chạy khi một API bất kỳ báo mất phiên. Trả hàm huỷ đăng ký. */
export function onSessionLost(handler: () => void) {
  sessionLostHandler = handler;
  return () => {
    if (sessionLostHandler === handler) sessionLostHandler = null;
  };
}

apiClient.interceptors.response.use(undefined, (error: unknown) => {
  if (isAxiosError(error) && error.response) {
    const code = (error.response.data as { code?: string } | undefined)?.code;
    const url = error.config?.url ?? '';
    if (code && SESSION_LOST.has(code) && !SELF_HANDLED.includes(url)) sessionLostHandler?.();
  }
  return Promise.reject(error);
});
