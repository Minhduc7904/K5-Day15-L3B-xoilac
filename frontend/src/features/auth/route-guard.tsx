'use client';

/**
 * Chặn route theo phiên. Admin và học sinh là hai phiên độc lập (cookie riêng) nên dùng song song được:
 * - `/admin/*` chỉ cần phiên admin. Chưa có thì chuyển tới `/login/admin`.
 * - Mọi trang khác (trừ trang chủ `/` và trang auth) cần phiên học sinh. Chưa có thì chuyển tới `/login`.
 * - Có phiên admin không ép người dùng khỏi trang học sinh và ngược lại.
 * - Đã đăng nhập mà mở trang auth: về trang chủ của phiên tương ứng (`/login/admin` xét phiên admin, còn lại xét phiên học sinh).
 * Đây chỉ là lớp UX. Quyền thật do backend kiểm ở từng API.
 */
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, type ReactNode } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { useAppSelector } from '@/store';
import type { AuthState } from './auth-slice';
import type { User } from './types';

export const ADMIN_LOGIN_PATH = '/login/admin';
const AUTH_PATHS = ['/login', '/register', '/forgot-password', '/verify-otp', '/reset-password'];
/** Trang mọi người đã đăng nhập đều xem được, bất kể vai trò. */
const SHARED_PATHS = ['/design-system'];

const under = (path: string, base: string) => path === base || path.startsWith(`${base}/`);

export const homeFor = (user: Pick<User, 'role'>) => (user.role === 'admin' ? '/admin' : '/dashboard');

const isAuthPage = (path: string) => AUTH_PATHS.some((base) => under(path, base));
/**
 * Khách chỉ xem được trang chủ (để biết Examind là gì) và các trang auth. Các trang học sinh
 * (`/dashboard`, `/exams`, `/results`, `/profile`) luôn yêu cầu đăng nhập.
 */
const isPublicPage = (path: string) => isAuthPage(path) || path === '/';

/** Hai phiên đăng nhập độc lập: học sinh (`auth`) và admin (`adminAuth`). */
export interface AuthSessions {
  student: AuthState;
  admin: AuthState;
}

const loginFor = (path: string, auth: AuthState) => {
  const base = under(path, '/admin') ? ADMIN_LOGIN_PATH : '/login';
  return auth.reason ? `${base}?reason=${auth.reason}` : base;
};

/** Trả đường dẫn cần chuyển tới, hoặc `null` nếu được ở lại. `undefined` khi chưa biết phiên. */
export function guardRedirect(path: string, sessions: AuthSessions): string | null | undefined {
  const { student, admin } = sessions;

  if (under(path, '/admin')) {
    if (admin.status === 'unknown') return undefined;
    return admin.user ? null : loginFor(path, admin);
  }
  if (path === ADMIN_LOGIN_PATH) return admin.user ? homeFor(admin.user) : null;

  if (student.status === 'unknown') return isPublicPage(path) ? null : undefined;
  if (!student.user) {
    if (isPublicPage(path)) return null;
    // Trang dùng chung cho cả hai vai trò: người đang đăng nhập admin cũng được xem.
    if (SHARED_PATHS.some((base) => under(path, base)) && admin.user) return null;
    return loginFor(path, student);
  }
  if (isAuthPage(path)) return homeFor(student.user);
  return null;
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const student = useAppSelector((s) => s.auth);
  const admin = useAppSelector((s) => s.adminAuth);
  const path = usePathname();
  const router = useRouter();
  const target = guardRedirect(path, { student, admin });
  const firstPath = useRef(true);

  // Sang trang khác (vd đăng nhập xong về `/dashboard`) thì luôn bắt đầu từ đầu trang, không giữ vị trí cuộn của
  // trang trước. Bỏ qua lần đầu để không phá việc trình duyệt nhảy tới `#neo` khi mở thẳng link.
  useEffect(() => {
    if (firstPath.current) {
      firstPath.current = false;
      return;
    }
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [path]);

  useEffect(() => {
    if (target) router.replace(target);
  }, [target, router]);

  // Trang auth luôn giữ nguyên trong lúc chuyển đi: gỡ ra rồi gắn lại sẽ chạy lại các bước chỉ làm
  // được một lần (vd /login/google đã dùng ticket), rồi báo lỗi giả.
  if (target === null || isAuthPage(path)) return children;
  return (
    <div className="grid min-h-dvh place-items-center">
      <Spinner size="lg" label={target ? 'Đang chuyển trang' : 'Đang kiểm tra phiên đăng nhập'} />
    </div>
  );
}
