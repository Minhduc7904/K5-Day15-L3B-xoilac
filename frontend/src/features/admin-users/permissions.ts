/**
 * Bản sao phía UI của hàm thuần can_manage ở backend (backend/app/usecase/user_management.py), CHỈ để ẩn
 * thao tác mà backend sẽ trả 403. Backend vẫn là nơi quyết định; sửa luật thì sửa cả hai chỗ.
 */
import type { Role, UpdateUserInput } from './types';

export interface Principal {
  user_id: number;
  role: Role;
  is_root: boolean;
}

export type Action = 'create' | 'update' | 'reset_password';
export type DenyCode = 'FORBIDDEN_ROLE' | 'CANNOT_MODIFY_ROOT' | 'CANNOT_MODIFY_SELF';

export function canManage(
  actor: Principal,
  target: Principal | null,
  action: Action,
  changes: UpdateUserInput & { role?: Role } = {},
): DenyCode | null {
  const wantsAdmin = changes.role === 'admin';
  if (action === 'create') return wantsAdmin && !actor.is_root ? 'FORBIDDEN_ROLE' : null;
  if (!target) return 'FORBIDDEN_ROLE';

  const isSelf = actor.user_id === target.user_id;
  const keys = Object.keys(changes);
  const onlyName = action === 'update' && keys.every((k) => k === 'display_name');

  if (target.is_root) {
    if (isSelf && onlyName) return null;
    return onlyName ? 'FORBIDDEN_ROLE' : 'CANNOT_MODIFY_ROOT';
  }
  if (isSelf && (changes.status === 'disabled' || (changes.role !== undefined && changes.role !== target.role))) {
    return 'CANNOT_MODIFY_SELF';
  }
  if (target.role === 'admin' && !actor.is_root) return 'FORBIDDEN_ROLE';
  if (wantsAdmin && target.role !== 'admin' && !actor.is_root) return 'FORBIDDEN_ROLE';
  return null;
}

export const DENY_MESSAGES: Record<DenyCode, string> = {
  FORBIDDEN_ROLE: 'Tài khoản không có quyền dùng chức năng này',
  CANNOT_MODIFY_ROOT: 'Không thể khóa, đổi vai trò, đổi email hay đặt lại mật khẩu của admin gốc',
  CANNOT_MODIFY_SELF: 'Không thể tự khóa hoặc tự hạ vai trò của chính mình',
};
