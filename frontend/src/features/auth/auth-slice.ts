import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { User } from './types';

/** Chỉ lưu `UserOut`, không lưu token (phiên do cookie HttpOnly của backend giữ). */
export interface AuthState {
  user: User | null;
  /** `unknown` cho tới khi splash kiểm xong phiên. */
  status: 'unknown' | 'authenticated' | 'guest';
}

const initialState: AuthState = { user: null, status: 'unknown' };

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    signedIn(state, action: PayloadAction<User>) {
      state.user = action.payload;
      state.status = 'authenticated';
    },
    signedOut(state) {
      state.user = null;
      state.status = 'guest';
    },
  },
});

export const { signedIn, signedOut } = authSlice.actions;
