import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AuthScope } from '@/lib/auth-scope';
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

/**
 * Hai phiên độc lập, mỗi phiên một slice: `auth` (học sinh) và `adminAuth` (admin). Slice chỉ nhận người dùng
 * đúng vai trò của nó nên đăng nhập bên này không ảnh hưởng bên kia.
 */
function createAuthSlice(name: string, role: User['role']) {
  const accepts = (user: User | null): user is User => user?.role === role;
  return createSlice({
    name,
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
        const user = accepts(action.payload) ? action.payload : null;
        state.user = user;
        state.status = user ? 'authenticated' : 'guest';
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
}

export const authSlice = createAuthSlice('auth', 'student');
export const adminAuthSlice = createAuthSlice('adminAuth', 'admin');

export const { sessionChecked, signedIn, signedOut, studentDisplayNameChanged } = authSlice.actions;
export const adminActions = adminAuthSlice.actions;

/** Đăng nhập xong: ghi người dùng vào phiên đúng vai trò (admin hoặc học sinh). */
export const signedInAs = (user: User) => (user.role === 'admin' ? adminActions.signedIn(user) : signedIn(user));

export const signedOutOf = (scope: AuthScope, reason?: SignOutReason) =>
  scope === 'admin' ? adminActions.signedOut(reason) : signedOut(reason);

export const sessionCheckedOf = (scope: AuthScope, user: User | null) =>
  scope === 'admin' ? adminActions.sessionChecked(user) : sessionChecked(user);

/** Chọn slice theo phạm vi: dùng trong `useAppSelector((s) => authOf(s, scope))`. */
export const authOf = (state: { auth: AuthState; adminAuth: AuthState }, scope: AuthScope): AuthState =>
  scope === 'admin' ? state.adminAuth : state.auth;
