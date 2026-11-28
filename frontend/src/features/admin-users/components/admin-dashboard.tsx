'use client';

/**
 * Trang /admin (#20): ô học sinh online + quản lý người dùng.
 * Chặn ở mức giao diện cho người chưa đăng nhập hoặc không phải admin; route guard đầy đủ thuộc #9.
 * Biết mình có phải admin gốc không bằng GET /admin/users/{id của mình} (UserOut của /auth/me không có is_root).
 */
import { useEffect, useState } from 'react';
import { Container } from '@/components/layout/container';
import { Button } from '@/components/ui/button';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { OnlineStudentsCard } from '@/features/admin-stats/online-students-card';
import { toApiError } from '@/lib/api-error';
import { useAppSelector } from '@/store';
import { adminUsersApi } from '../api';
import type { Principal } from '../permissions';
import { UserManagement } from './user-management';

export function AdminDashboard() {
  const { user, status } = useAppSelector((s) => s.auth);
  const [actor, setActor] = useState<Principal | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || user.role !== 'admin') return;
    let cancelled = false;
    adminUsersApi
      .get(user.user_id)
      .then((me) => !cancelled && setActor({ user_id: me.user_id, role: me.role, is_root: me.is_root }))
      .catch((e) => !cancelled && setError(toApiError(e).message));
    return () => {
      cancelled = true;
    };
  }, [user]);

  let body;
  if (status === 'unknown') body = <Skeleton className="h-64 w-full" />;
  else if (!user)
    body = (
      <Alert tone="info" title="Cần đăng nhập" action={<Button href="/login" size="sm">Đăng nhập</Button>}>
        Đăng nhập bằng tài khoản quản trị để dùng trang này.
      </Alert>
    );
  else if (user.role !== 'admin') body = <Alert tone="warning" title="Tài khoản không có quyền dùng chức năng này" />;
  else if (error) body = <Alert tone="danger" title="Không tải được thông tin tài khoản">{error}</Alert>;
  else if (!actor) body = <Skeleton className="h-64 w-full" />;
  else
    body = (
      <div className="grid gap-6 lg:grid-cols-[20rem_1fr] lg:items-start">
        <OnlineStudentsCard />
        <UserManagement actor={actor} />
      </div>
    );

  return (
    <Container size="full" className="py-8">
      {body}
    </Container>
  );
}
