/**
 * Mock API quản lý người dùng (#20), chạy trong trình duyệt, lưu ở sessionStorage.
 * admin@example.com là admin gốc; admin2@example.com là admin thường để thử giao diện bị giới hạn.
 * Luật phân quyền dùng chung canManage với UI. Không dùng dữ liệu thật.
 */
import { getMockCurrentEmail } from '@/features/auth/mock';
import { ApiError } from '@/lib/api-error';
import { canManage, DENY_MESSAGES } from './permissions';
import type { AdminUser, CreateUserInput, UpdateUserInput, UserList, UserQuery } from './types';
import { PASSWORD_MAX, PASSWORD_MIN } from './types';

const STORAGE_KEY = 'examind:mock-admin-users';
const delay = (ms = 350) => new Promise((resolve) => window.setTimeout(resolve, ms));

function seed(): AdminUser[] {
  const base = { created_by: null, last_login_at: null, is_root: false, status: 'active' as const };
  const students = Array.from({ length: 18 }, (_, i) => ({
    ...base,
    user_id: 10 + i,
    email: `hocsinh${String(i + 1).padStart(2, '0')}@example.com`,
    display_name: `Học sinh ${i + 1}`,
    role: 'student' as const,
    created_at: '2026-11-28T08:00:00.000000Z',
    created_by: 2,
  }));
  return [
    { ...base, user_id: 1, email: 'hs01@example.com', display_name: 'Học sinh 01', role: 'student', created_at: '2026-11-27T15:52:23.845134Z' },
    { ...base, user_id: 2, email: 'admin@example.com', display_name: 'Quản trị', role: 'admin', is_root: true, created_at: '2026-11-27T15:52:41.085593Z', last_login_at: '2026-11-28T09:00:00.000000Z' },
    { ...base, user_id: 3, email: 'khoa@example.com', display_name: 'Tài khoản bị khoá', role: 'student', status: 'disabled', created_at: '2026-11-27T16:00:00.000000Z' },
    { ...base, user_id: 4, email: 'admin2@example.com', display_name: 'Admin thường', role: 'admin', created_at: '2026-11-28T07:00:00.000000Z', created_by: 2 },
    ...students,
  ];
}

function load(): AdminUser[] {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as AdminUser[];
  } catch {
    /* bỏ qua */
  }
  return seed();
}

function save(users: AdminUser[]) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(users));
  } catch {
    /* bỏ qua */
  }
}

function actor(users: AdminUser[]): AdminUser {
  const email = getMockCurrentEmail();
  const me = users.find((u) => u.email === email);
  if (!me) throw new ApiError('SESSION_MISSING', 'Chưa đăng nhập', 401);
  if (me.role !== 'admin') throw new ApiError('FORBIDDEN_ROLE', DENY_MESSAGES.FORBIDDEN_ROLE, 403);
  return me;
}

function find(users: AdminUser[], id: number): AdminUser {
  const user = users.find((u) => u.user_id === id);
  if (!user) throw new ApiError('USER_NOT_FOUND', 'Không có tài khoản này', 404);
  return user;
}

function deny(code: ReturnType<typeof canManage>) {
  if (code) throw new ApiError(code, DENY_MESSAGES[code], 403);
}

function checkPassword(password: string) {
  if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
    throw new ApiError('VALIDATION', 'Thông tin chưa hợp lệ.', 422, { password: `Mật khẩu cần từ ${PASSWORD_MIN} đến ${PASSWORD_MAX} ký tự.` });
  }
}

export const mockAdminUsersApi = {
  async list(query: UserQuery): Promise<UserList> {
    await delay();
    const users = load();
    actor(users);
    const q = query.q?.trim().toLowerCase();
    const matched = users
      .filter((u) => !query.role || u.role === query.role)
      .filter((u) => !query.status || u.status === query.status)
      .filter((u) => !q || u.email.includes(q) || (u.display_name ?? '').toLowerCase().includes(q))
      .sort((a, b) => a.user_id - b.user_id);
    const start = (query.page - 1) * query.page_size;
    return { items: matched.slice(start, start + query.page_size), total: matched.length, page: query.page, page_size: query.page_size };
  },

  async get(id: number): Promise<AdminUser> {
    await delay(150);
    const users = load();
    actor(users);
    return find(users, id);
  },

  async create(input: CreateUserInput): Promise<AdminUser> {
    await delay();
    const users = load();
    const me = actor(users);
    deny(canManage(me, null, 'create', { role: input.role }));
    checkPassword(input.password);
    const email = input.email.trim().toLowerCase();
    if (users.some((u) => u.email === email)) throw new ApiError('EMAIL_TAKEN', 'Email này đã được đăng ký', 409);
    const user: AdminUser = {
      user_id: Math.max(...users.map((u) => u.user_id)) + 1,
      email,
      display_name: input.display_name?.trim() || null,
      role: input.role,
      status: 'active',
      is_root: false,
      created_at: new Date().toISOString(),
      created_by: me.user_id,
      last_login_at: null,
    };
    save([...users, user]);
    return user;
  },

  async update(id: number, changes: UpdateUserInput): Promise<AdminUser> {
    await delay();
    const users = load();
    const me = actor(users);
    const target = find(users, id);
    deny(canManage(me, target, 'update', changes));
    if (changes.email !== undefined) {
      const email = changes.email.trim().toLowerCase();
      if (users.some((u) => u.email === email && u.user_id !== id)) throw new ApiError('EMAIL_TAKEN', 'Email này đã được đăng ký', 409);
      changes = { ...changes, email };
    }
    const updated: AdminUser = { ...target, ...changes };
    save(users.map((u) => (u.user_id === id ? updated : u)));
    return updated;
  },

  async resetPassword(id: number, password: string): Promise<void> {
    await delay();
    const users = load();
    const me = actor(users);
    deny(canManage(me, find(users, id), 'reset_password'));
    checkPassword(password);
  },
};
