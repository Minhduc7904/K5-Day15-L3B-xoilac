'use client';

/**
 * Trang /admin/users (#20, tách khỏi /admin ở #11): quản lý người dùng.
 * AdminShell đã chặn người không phải admin. Biết mình có phải admin gốc không bằng GET /admin/users/{id của mình}
 * (UserOut của /auth/me không có is_root).
 */
import { useEffect, useState } from 'react';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { PageHeader } from '@/features/admin/admin-ui';
import { toApiError } from '@/lib/api-error';
import { useAppSelector } from '@/store';
import { adminUsersApi } from '../api';
import type { Principal } from '../permissions';
import { UserManagement } from './user-management';

export function UsersPage() {
  const user = useAppSelector((s) => s.adminAuth.user);
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

  return (
    <>
      <PageHeader title="Người dùng" description="Tạo, sửa, khoá tài khoản học sinh và admin." />
      {error ? (
        <Alert tone="danger" title="Không tải được thông tin tài khoản">{error}</Alert>
      ) : actor ? (
        <UserManagement actor={actor} />
      ) : (
        <Skeleton className="h-64 w-full" />
      )}
    </>
  );
}
