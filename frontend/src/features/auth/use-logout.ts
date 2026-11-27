'use client';

import { useState } from 'react';
import { useAppDispatch } from '@/store';
import { authApi } from './api';
import { signedOut } from './auth-slice';

export function useLogout() {
  const dispatch = useAppDispatch();
  const [leaving, setLeaving] = useState(false);

  async function logout() {
    setLeaving(true);
    try {
      await authApi.logout();
    } catch {
      // Xóa trạng thái đăng nhập phía client nếu yêu cầu đăng xuất gặp lỗi mạng.
    } finally {
      dispatch(signedOut('logged-out'));
      setLeaving(false);
    }
  }

  return { leaving, logout };
}
