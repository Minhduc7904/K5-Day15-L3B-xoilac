/**
 * Đổi lỗi Axios thành `ApiError` có `code` theo hợp đồng backend: body lỗi `{"detail", "code"}`,
 * lỗi 422 của FastAPI có `detail` là mảng lỗi theo trường. Dùng cho các feature mới (#20).
 */
import { isAxiosError } from 'axios';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number,
    /** Lỗi theo trường (422). */
    public fieldErrors?: Record<string, string>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function toApiError(error: unknown, fieldMessages: Record<string, string> = {}): ApiError {
  if (error instanceof ApiError) return error;
  if (!isAxiosError(error)) return new ApiError('UNKNOWN', 'Đã có lỗi không mong muốn.');
  if (!error.response) return new ApiError('NETWORK', 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại nhé.');

  const { status, data } = error.response as { status: number; data: { detail?: unknown; code?: string } };
  if (status === 422 && Array.isArray(data?.detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const item of data.detail as Array<{ loc?: unknown[] }>) {
      const field = String(item.loc?.[item.loc.length - 1] ?? '');
      if (field) fieldErrors[field] = fieldMessages[field] ?? 'Giá trị chưa hợp lệ.';
    }
    return new ApiError('VALIDATION', 'Thông tin chưa hợp lệ.', status, fieldErrors);
  }
  const message = typeof data?.detail === 'string' ? data.detail : 'Đã có lỗi từ máy chủ.';
  return new ApiError(data?.code ?? 'UNKNOWN', message, status);
}

export async function request<T>(send: () => Promise<{ data: T }>, fieldMessages?: Record<string, string>): Promise<T> {
  try {
    return (await send()).data;
  } catch (error) {
    throw toApiError(error, fieldMessages);
  }
}
