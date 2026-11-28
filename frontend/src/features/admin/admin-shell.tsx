'use client';

/**
 * Khung khu quản trị (#11): thanh điều hướng liệt kê mọi trang admin, đánh dấu trang đang mở và chặn theo vai trò.
 * AuthGuard đã chuyển học sinh khỏi /admin; ở đây chặn thêm lần nữa để không bao giờ render trang quản trị cho
 * người không phải admin. Quyền thật do backend kiểm ở từng API (AdminDep).
 */
import { FileQuestionMark, FileUp, LayoutDashboard, LayoutTemplate, ListTree, Users } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';
import { Container } from '@/components/layout/container';
import { Button } from '@/components/ui/button';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { ADMIN_LOGIN_PATH } from '@/features/auth/route-guard';
import { useAppSelector } from '@/store';

export const ADMIN_LINKS = [
  { href: '/admin', label: 'Tổng quan', icon: LayoutDashboard },
  { href: '/admin/questions', label: 'Câu hỏi', icon: FileQuestionMark },
  { href: '/admin/chapters', label: 'Chương', icon: ListTree },
  { href: '/admin/pdf-imports', label: 'Nhập đề PDF', icon: FileUp },
  { href: '/admin/exam-templates', label: 'Mẫu cấu trúc đề', icon: LayoutTemplate },
  { href: '/admin/users', label: 'Người dùng', icon: Users },
] as const;

export const isActiveLink = (path: string, href: string) =>
  href === '/admin' ? path === '/admin' : path === href || path.startsWith(`${href}/`);

function AdminNav({ path }: { path: string }) {
  return (
    <nav aria-label="Điều hướng quản trị">
      <ul className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
        {ADMIN_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isActiveLink(path, href);
          return (
            <li key={href} className="shrink-0">
              <Link
                href={href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-2.5 rounded-xl px-3 py-2 text-label transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                  active
                    ? 'bg-primary-subtle font-semibold text-primary'
                    : 'text-muted-foreground hover:bg-surface-muted hover:text-foreground',
                )}
              >
                <Icon className="size-4.5 shrink-0" aria-hidden="true" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function AdminShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { user, status } = useAppSelector((s) => s.adminAuth);

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
  return (
    <Container size="full" className="grid gap-6 py-6 lg:grid-cols-[14rem_minmax(0,1fr)] lg:items-start lg:py-8">
      {allowed ? (
        <aside className="lg:sticky lg:top-6">
          <AdminNav path={path} />
        </aside>
      ) : (
        <div className="hidden lg:block" />
      )}
      <main id="noi-dung" className="min-w-0">
        {body}
      </main>
    </Container>
  );
}
