'use client';

/**
 * Chặn route theo phiên và vai trò. Web chỉ có hai loại người dùng: học sinh và admin.
 * - Chưa đăng nhập: chỉ vào được các trang auth, mọi trang khác chuyển tới /login.
 * - Học sinh: không vào /admin. Admin: chỉ ở /admin.
 * - Đã đăng nhập mà mở trang auth: chuyển về trang chủ theo vai trò.
 * Đây chỉ là lớp UX. Quyền thật do backend kiểm ở từng API.
 */
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { useAppSelector } from '@/store';
import type { AuthState } from './auth-slice';
import type { User } from './types';

const AUTH_PATHS = ['/login', '/register', '/forgot-password', '/verify-otp', '/reset-password'];
/** Trang mọi người đã đăng nhập đều xem được, bất kể vai trò. */
const SHARED_PATHS = ['/design-system'];

const under = (path: string, base: string) => path === base || path.startsWith(`${base}/`);

export const homeFor = (user: Pick<User, 'role'>) => (user.role === 'admin' ? '/admin' : '/');

/** Trả đường dẫn cần chuyển tới, hoặc `null` nếu được ở lại. `undefined` khi chưa biết phiên. */
export function guardRedirect(path: string, auth: AuthState): string | null | undefined {
  const isAuthPage = AUTH_PATHS.some((base) => under(path, base));
  if (auth.status === 'unknown') return isAuthPage ? null : undefined;
  const { user } = auth;
  if (!user) return isAuthPage ? null : auth.reason ? `/login?reason=${auth.reason}` : '/login';
  if (isAuthPage) return homeFor(user);
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

  useEffect(() => {
    if (target) router.replace(target);
  }, [target, router]);

  if (target === null) return children;
  return (
    <div className="grid min-h-dvh place-items-center">
      <Spinner size="lg" label={target ? 'Đang chuyển trang' : 'Đang kiểm tra phiên đăng nhập'} />
    </div>
  );
}
