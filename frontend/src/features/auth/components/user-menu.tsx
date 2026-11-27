'use client';

import { LogOut } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppDispatch, useAppSelector } from '@/store';
import { authApi } from '../api';
import { signedOut } from '../auth-slice';

/** Tên người dùng và nút đăng xuất trên thanh điều hướng. Đăng xuất xong `AuthGuard` đưa về /login. */
export function UserMenu() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const [leaving, setLeaving] = useState(false);
  const hydrated = useHydrated();

  if (!hydrated || !user) return <Skeleton className="h-9 w-48 rounded-xl" />;

  const name = user.display_name ?? user.email;
  const logout = async () => {
    setLeaving(true);
    try {
      await authApi.logout();
    } catch {
      // Backend luôn trả 204; lỗi mạng thì vẫn xoá trạng thái phía client.
    }
    dispatch(signedOut('logged-out'));
  };

  return (
    <>
      <span className="flex min-w-0 items-center gap-2 rounded-xl bg-surface px-3 py-1.5 text-label text-foreground">
        <span
          className="flex size-7 items-center justify-center rounded-full bg-primary text-caption font-bold text-primary-foreground"
          aria-hidden="true"
        >
          {name.charAt(0).toUpperCase()}
        </span>
        <span className="max-w-28 truncate sm:max-w-40">{name}</span>
        {user.role === 'admin' && (
          <span className="hidden text-caption whitespace-nowrap text-muted-foreground sm:inline">· Quản trị</span>
        )}
      </span>
      <Button variant="ghost" size="sm" leftIcon={<LogOut aria-hidden="true" />} onClick={logout} loading={leaving}>
        Đăng xuất
      </Button>
    </>
  );
}
