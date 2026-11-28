/**
 * Lớp gọi API của feature quản lý người dùng (#20): /api/v1/admin/users (qua rewrites của Next.js).
 * Mọi màn chỉ gọi qua `adminUsersApi`. Lỗi mất phiên do interceptor của lib/api-client xử lý chung.
 */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';
import type { AdminUser, CreateUserInput, UpdateUserInput, UserList, UserQuery } from './types';
import { PASSWORD_MAX, PASSWORD_MIN } from './types';

const FIELD_MESSAGES: Record<string, string> = {
  email: 'Email chưa đúng định dạng.',
  password: `Mật khẩu cần từ ${PASSWORD_MIN} đến ${PASSWORD_MAX} ký tự.`,
  display_name: 'Tên hiển thị dài tối đa 100 ký tự.',
};

const opts = { withCredentials: true };

export const adminUsersApi = {
  list: (query: UserQuery) =>
    request<UserList>(() => apiClient.get('/admin/users', { ...opts, params: { ...query, q: query.q || undefined } })),
  get: (id: number) => request<AdminUser>(() => apiClient.get(`/admin/users/${id}`, opts)),
  create: (input: CreateUserInput) => request<AdminUser>(() => apiClient.post('/admin/users', input, opts), FIELD_MESSAGES),
  update: (id: number, changes: UpdateUserInput) =>
    request<AdminUser>(() => apiClient.patch(`/admin/users/${id}`, changes, opts), FIELD_MESSAGES),
  resetPassword: (id: number, password: string) =>
    request<void>(() => apiClient.post(`/admin/users/${id}/reset-password`, { password }, opts), FIELD_MESSAGES),
};
