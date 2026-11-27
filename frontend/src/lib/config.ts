export const mockMode = process.env.NEXT_PUBLIC_MOCK_MODE !== 'false';
export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

function originOf(url: string): string {
  try {
    return new URL(url).origin;
  } catch {
    return ''; // apiBaseUrl tương đối (qua rewrites): cùng origin với trang
  }
}

/**
 * Socket.IO nối THẲNG backend (#20): Vercel rewrites không chuyển WebSocket.
 * Mặc định lấy origin của NEXT_PUBLIC_API_BASE_URL. Origin của trang phải nằm trong CORS_ORIGINS của backend.
 */
export const socketUrl = process.env.NEXT_PUBLIC_SOCKET_URL || originOf(apiBaseUrl);
