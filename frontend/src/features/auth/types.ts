/** Khớp `UserOut` trong docs/api/auth-api.md. */
export interface User {
  user_id: number;
  email: string;
  role: 'student' | 'admin';
  status: 'active' | 'disabled';
  display_name: string | null;
  created_at: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput {
  email: string;
  password: string;
  display_name?: string;
}

export type AuthErrorCode =
  // Có trong hợp đồng backend #8
  | 'INVALID_CREDENTIALS'
  | 'ACCOUNT_DISABLED'
  | 'EMAIL_TAKEN'
  | 'SESSION_MISSING'
  | 'SESSION_INVALID'
  | 'SESSION_EXPIRED'
  | 'SESSION_REVOKED'
  // Đề xuất cho luồng quên mật khẩu, backend chưa có
  | 'OTP_INVALID'
  | 'OTP_EXPIRED'
  | 'TOO_MANY_ATTEMPTS'
  | 'RESET_TOKEN_INVALID'
  // Phía client
  | 'VALIDATION'
  | 'NETWORK'
  | 'UNKNOWN';

export class AuthError extends Error {
  constructor(
    public code: AuthErrorCode,
    message: string,
    public status?: number,
    /** Lỗi theo trường (422). */
    public fieldErrors?: Record<string, string>,
    /** Số lần nhập OTP còn lại, khi `code` là OTP_INVALID. */
    public remainingAttempts?: number,
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

export function toAuthError(error: unknown): AuthError {
  if (error instanceof AuthError) return error;
  return new AuthError('UNKNOWN', 'Đã có lỗi không mong muốn. Bạn thử lại sau nhé.');
}
