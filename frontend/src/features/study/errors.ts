import { isAxiosError } from 'axios';

/** Lỗi "không tìm thấy" để trang hiện trạng thái phù hợp (kiểm bằng `error.name === 'NotFoundError'`). */
export function notFoundError(message: string): Error {
  const error = new Error(message);
  error.name = 'NotFoundError';
  return error;
}

/** Đổi phản hồi 404 của server thành `NotFoundError`; lỗi khác giữ nguyên. */
export async function orNotFound<T>(request: Promise<T>, message: string): Promise<T> {
  try {
    return await request;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) throw notFoundError(message);
    throw error;
  }
}
