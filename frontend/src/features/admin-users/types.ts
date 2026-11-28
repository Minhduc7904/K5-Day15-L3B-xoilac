/** Khớp docs/api/user-management-api.md (#20). */
export type Role = 'student' | 'admin';
export type Status = 'active' | 'disabled';

export interface AdminUser {
  user_id: number;
  email: string;
  display_name: string | null;
  role: Role;
  status: Status;
  is_root: boolean;
  created_at: string;
  created_by: number | null;
  last_login_at: string | null;
}

export interface UserList {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserQuery {
  role?: Role;
  status?: Status;
  q?: string;
  page: number;
  page_size: number;
}

export interface CreateUserInput {
  email: string;
  password: string;
  role: Role;
  display_name?: string;
}

export type UpdateUserInput = Partial<Pick<AdminUser, 'display_name' | 'email' | 'role' | 'status'>>;

/** Mật khẩu mới: cùng PASSWORD_MIN / PASSWORD_MAX của backend. */
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;
