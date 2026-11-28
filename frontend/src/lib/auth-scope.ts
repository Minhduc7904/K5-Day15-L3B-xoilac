/**
 * Phạm vi phiên đăng nhập. Admin và học sinh có cookie phiên riêng nên đăng nhập song song trong cùng một trình duyệt.
 * Trang `/admin/*` dùng phiên admin, mọi trang còn lại dùng phiên học sinh. Mỗi request gửi header này để backend
 * biết đọc cookie nào (backend: `app/api/cookies.py`).
 */
export type AuthScope = 'student' | 'admin';

export const SCOPE_HEADER = 'X-Auth-Scope';

export function scopeForPath(path: string): AuthScope {
  return path === '/admin' || path.startsWith('/admin/') ? 'admin' : 'student';
}
