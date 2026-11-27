import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { User } from './types';

/** Chỉ lưu `UserOut`, không lưu token (phiên do cookie HttpOnly của backend giữ). */
export interface AuthState {
  user: User | null;
  /** `unknown` cho tới khi splash kiểm xong phiên. */
  status: 'unknown' | 'authenticated' | 'guest';
  /** Lý do mất phiên, để trang đăng nhập hiện thông báo phù hợp. */
  reason: SignOutReason | null;
}

export type SignOutReason = 'session-expired' | 'logged-out';

const initialState: AuthState = { user: null, status: 'unknown', reason: null };

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    signedIn(state, action: PayloadAction<User>) {
      state.user = action.payload;
      state.status = 'authenticated';
      state.reason = null;
    },
    /**
     * Kết quả kiểm phiên lúc khởi động. Chỉ áp dụng khi chưa biết phiên: nếu trong lúc chờ `/auth/me`
     * người dùng đã đăng nhập (vd trang /login/google đổi ticket xong) thì kết quả cũ bị bỏ qua.
     */
    sessionChecked(state, action: PayloadAction<User | null>) {
      if (state.status !== 'unknown') return;
      state.user = action.payload;
      state.status = action.payload ? 'authenticated' : 'guest';
    },
    studentDisplayNameChanged(state, action: PayloadAction<{ userId: number; name: string | null }>) {
      if (state.user?.user_id === action.payload.userId) state.user.display_name = action.payload.name;
    },
    signedOut(state, action: PayloadAction<SignOutReason | undefined>) {
      state.user = null;
      state.status = 'guest';
      state.reason = action.payload ?? null;
    },
  },
});

export const { sessionChecked, signedIn, signedOut, studentDisplayNameChanged } = authSlice.actions;
