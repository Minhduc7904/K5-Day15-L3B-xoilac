'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppDispatch, useAppSelector } from '@/store';
import { authApi } from '../api';
import { signedOut } from '../auth-slice';

/** Báo khi người dùng đã đăng nhập mà vẫn mở trang đăng nhập/đăng ký. */
export function SignedInNotice() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const toast = useToast();
  const [leaving, setLeaving] = useState(false);
  const hydrated = useHydrated();

  if (!hydrated || !user) return null;

  const logout = async () => {
    setLeaving(true);
    try {
      await authApi.logout();
      dispatch(signedOut());
      toast({ tone: 'info', title: 'Đã đăng xuất' });
    } finally {
      setLeaving(false);
    }
  };

  return (
    <Alert
      tone="info"
      title={`Bạn đang đăng nhập là ${user.display_name ?? user.email}`}
      action={
        <div className="flex flex-wrap gap-2">
          <Button size="sm" href={user.role === 'admin' ? '/admin' : '/'}>
            Tiếp tục
          </Button>
          <Button size="sm" variant="outline" onClick={logout} loading={leaving}>
            Đăng xuất
          </Button>
        </div>
      }
    >
      Muốn dùng tài khoản khác thì đăng xuất trước nhé.
    </Alert>
  );
}
