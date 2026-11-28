'use client';

import { useState } from 'react';
import { useAppDispatch } from '@/store';
import { authApi } from './api';
import type { AuthScope } from '@/lib/auth-scope';
import { signedOutOf } from './auth-slice';

/** Đăng xuất một phiên. Phiên còn lại (admin hoặc học sinh) vẫn giữ nguyên. */
export function useLogout(scope: AuthScope = 'student') {
  const dispatch = useAppDispatch();
  const [leaving, setLeaving] = useState(false);

  async function logout() {
    setLeaving(true);
    try {
      await authApi.logout(scope);
    } catch {
      // Xóa trạng thái đăng nhập phía client nếu yêu cầu đăng xuất gặp lỗi mạng.
    } finally {
      dispatch(signedOutOf(scope, 'logged-out'));
      setLeaving(false);
    }
  }

  return { leaving, logout };
}
