'use client';

/**
 * Khung khu quản trị (#11): thanh bên điều hướng nhóm theo công việc, thanh trên cùng và vùng nội dung.
 * AuthGuard đã chuyển học sinh khỏi /admin; ở đây chặn thêm lần nữa để không bao giờ render trang quản trị cho
 * người không phải admin. Quyền thật do backend kiểm ở từng API (AdminDep).
 */
import { Menu } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Logo } from '@/components/layout/logo';
import { Button, IconButton } from '@/components/ui/button';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { UserMenu } from '@/features/auth/components/user-menu';
import { ADMIN_LOGIN_PATH } from '@/features/auth/route-guard';
import { useAppSelector } from '@/store';
import { AdminDrawer, AdminSidebar } from './admin-sidebar';
import { activeLabel } from './admin-nav';

export { ADMIN_LINKS, isActiveLink } from './admin-nav';

const COLLAPSED_KEY = 'admin.sidebar.collapsed';

/** Trạng thái thu gọn lưu ở trình duyệt. Đọc sau khi mount để HTML lúc hydrate khớp server; không có storage thì vẫn chạy. */
function useSidebarCollapsed() {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- đọc localStorage chỉ làm được sau khi mount
      setCollapsed(window.localStorage.getItem(COLLAPSED_KEY) === '1');
    } catch {
      /* storage bị chặn: giữ mặc định mở rộng */
    }
  }, []);

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(COLLAPSED_KEY, next ? '1' : '0');
      } catch {
        /* bỏ qua */
      }
      return next;
    });
  }, []);

  return [collapsed, toggle] as const;
}

export function AdminShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { user, status } = useAppSelector((s) => s.adminAuth);
  const [collapsed, toggleCollapsed] = useSidebarCollapsed();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  let body: ReactNode;
  if (status === 'unknown') body = <Skeleton className="h-64 w-full" />;
  else if (!user)
    body = (
      <Alert tone="info" title="Cần đăng nhập" action={<Button href={ADMIN_LOGIN_PATH} size="sm">Đăng nhập</Button>}>
        Đăng nhập bằng tài khoản quản trị để dùng trang này.
      </Alert>
    );
  else if (user.role !== 'admin') body = <Alert tone="warning" title="Tài khoản không có quyền dùng chức năng này" />;
  else body = children;

  const allowed = user?.role === 'admin';
  const section = activeLabel(path);

  return (
    <div
      className={cn(
        'min-h-dvh lg:grid lg:transition-[grid-template-columns] lg:duration-200 motion-reduce:transition-none',
        allowed && (collapsed ? 'lg:grid-cols-[4.5rem_minmax(0,1fr)]' : 'lg:grid-cols-[15.5rem_minmax(0,1fr)]'),
      )}
    >
      <a
        href="#noi-dung"
        className="sr-only z-[110] rounded-lg bg-primary px-4 py-2 text-label text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Bỏ qua tới nội dung
      </a>

      {allowed && <AdminSidebar path={path} collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />}
      {allowed && <AdminDrawer open={drawerOpen} path={path} onClose={closeDrawer} />}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background px-4 sm:px-6 lg:px-8">
          {allowed && (
            <IconButton
              className="lg:hidden"
              label="Mở menu"
              aria-haspopup="dialog"
              aria-expanded={drawerOpen}
              onClick={() => setDrawerOpen(true)}
            >
              <Menu aria-hidden="true" />
            </IconButton>
          )}
          <span className={cn(allowed && 'lg:hidden')}>
            <Logo href="/admin" />
          </span>
          {allowed && (
            <p className="hidden min-w-0 truncate text-label text-muted-foreground lg:block">
              Quản trị{section && <span aria-hidden="true"> / </span>}
              {section && <span className="font-semibold text-foreground">{section}</span>}
            </p>
          )}
          <div className="ml-auto hidden items-center gap-2 sm:flex">
            <UserMenu scope="admin" />
          </div>
        </header>

        <main id="noi-dung" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-7xl">{body}</div>
        </main>
      </div>
    </div>
  );
}
