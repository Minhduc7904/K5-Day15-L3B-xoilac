'use client';

/**
 * Chặn route theo phiên và vai trò. Web chỉ có hai loại người dùng: học sinh và admin.
 * - Chưa đăng nhập: vào được trang chủ `/` (landing) và các trang auth, mọi trang khác chuyển tới /login.
 * - Học sinh: không vào /admin. Admin: chỉ ở /admin.
 * - Đã đăng nhập mà mở trang auth: chuyển về trang chủ theo vai trò.
 * Đây chỉ là lớp UX. Quyền thật do backend kiểm ở từng API.
 */
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, type ReactNode } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { useAppSelector } from '@/store';
import type { AuthState } from './auth-slice';
import type { User } from './types';

const AUTH_PATHS = ['/login', '/register', '/forgot-password', '/verify-otp', '/reset-password'];
/** Trang mọi người đã đăng nhập đều xem được, bất kể vai trò. */
const SHARED_PATHS = ['/design-system'];

const under = (path: string, base: string) => path === base || path.startsWith(`${base}/`);

export const homeFor = (user: Pick<User, 'role'>) => (user.role === 'admin' ? '/admin' : '/');

const isAuthPage = (path: string) => AUTH_PATHS.some((base) => under(path, base));
/**
 * Khách chỉ xem được trang chủ (để biết Examind là gì) và các trang auth. Các trang học sinh
 * (`/dashboard`, `/exams`, `/results`, `/profile`) luôn yêu cầu đăng nhập, kể cả khi dữ liệu là mock.
 */
const isPublicPage = (path: string) => isAuthPage(path) || path === '/';

/** Trả đường dẫn cần chuyển tới, hoặc `null` nếu được ở lại. `undefined` khi chưa biết phiên. */
export function guardRedirect(path: string, auth: AuthState): string | null | undefined {
  const authPage = isAuthPage(path);
  if (auth.status === 'unknown') return isPublicPage(path) ? null : undefined;
  const { user } = auth;
  if (!user) return isPublicPage(path) ? null : auth.reason ? `/login?reason=${auth.reason}` : '/login';
  if (authPage) return homeFor(user);
  if (SHARED_PATHS.some((base) => under(path, base))) return null;
  const inAdmin = under(path, '/admin');
  if (user.role === 'admin' && !inAdmin) return '/admin';
  if (user.role !== 'admin' && inAdmin) return '/';
  return null;
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const auth = useAppSelector((s) => s.auth);
  const path = usePathname();
  const router = useRouter();
  const target = guardRedirect(path, auth);
  const firstPath = useRef(true);

  // Sang trang khác (vd đăng nhập xong về `/`) thì luôn bắt đầu từ đầu trang, không giữ vị trí cuộn của
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
