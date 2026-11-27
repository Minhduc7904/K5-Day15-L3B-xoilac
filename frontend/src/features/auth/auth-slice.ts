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
    signedOut(state, action: PayloadAction<SignOutReason | undefined>) {
      state.user = null;
      state.status = 'guest';
      state.reason = action.payload ?? null;
    },
  },
});

export const { signedIn, signedOut } = authSlice.actions;
