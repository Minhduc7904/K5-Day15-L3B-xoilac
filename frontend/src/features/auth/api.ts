/**
 * Lớp gọi API của feature auth. Mọi trang auth chỉ gọi qua `authApi`.
 * Mặc định dùng mock (`NEXT_PUBLIC_MOCK_MODE` khác `false`). Đổi sang backend thật chỉ cần tắt cờ mock.
 *
 * login, register, logout, me: theo hợp đồng có sẵn của #8 (docs/api/auth-api.md).
 * forgotPassword, verifyOtp, resetPassword: hợp đồng ĐỀ XUẤT, backend chưa có endpoint.
 */
import { isAxiosError } from 'axios';
import { apiClient } from '@/lib/api-client';
import { mockMode } from '@/lib/config';
import { mockAuthApi } from './mock';
import { AuthError, type AuthErrorCode, type LoginInput, type RegisterInput, type User } from './types';

const FIELD_MESSAGES: Record<string, string> = {
  email: 'Email chưa đúng định dạng.',
  password: 'Mật khẩu cần từ 6 đến 128 ký tự.',
  display_name: 'Tên hiển thị dài tối đa 100 ký tự.',
};

function fromAxios(error: unknown): AuthError {
  if (!isAxiosError(error)) return new AuthError('UNKNOWN', 'Đã có lỗi không mong muốn.');
  if (!error.response) return new AuthError('NETWORK', 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại nhé.');

  const { status, data } = error.response as { status: number; data: { detail?: unknown; code?: string } };
  if (status === 422 && Array.isArray(data?.detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const item of data.detail as Array<{ loc?: unknown[] }>) {
      const field = String(item.loc?.[1] ?? '');
      if (field) fieldErrors[field] = FIELD_MESSAGES[field] ?? 'Giá trị chưa hợp lệ.';
    }
    return new AuthError('VALIDATION', 'Thông tin chưa hợp lệ.', status, fieldErrors);
  }
  const message = typeof data?.detail === 'string' ? data.detail : 'Đã có lỗi từ máy chủ.';
  return new AuthError((data?.code as AuthErrorCode) ?? 'UNKNOWN', message, status);
}

async function call<T>(request: () => Promise<{ data: T }>): Promise<T> {
  try {
    return (await request()).data;
  } catch (error) {
    throw fromAxios(error);
  }
}

const withCookie = { withCredentials: true };

const httpAuthApi = {
  login: (input: LoginInput) => call<User>(() => apiClient.post('/auth/login', input, withCookie)),
  register: (input: RegisterInput) => call<User>(() => apiClient.post('/auth/register', input, withCookie)),
  logout: () => call<void>(() => apiClient.post('/auth/logout', undefined, withCookie)),
  me: () => call<User>(() => apiClient.get('/auth/me', withCookie)),
  forgotPassword: (email: string) => call<void>(() => apiClient.post('/auth/password/forgot', { email })),
  verifyOtp: (email: string, otp: string) =>
    call<{ reset_token: string }>(() => apiClient.post('/auth/password/verify-otp', { email, otp })),
  resetPassword: (resetToken: string, password: string) =>
    call<void>(() => apiClient.post('/auth/password/reset', { reset_token: resetToken, password })),
};

export const authApi: typeof httpAuthApi = mockMode ? mockAuthApi : httpAuthApi;
