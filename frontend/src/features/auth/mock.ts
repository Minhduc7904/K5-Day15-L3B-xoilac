/**
 * Mock API auth chạy trong trình duyệt, theo bảng mock trong docs/api/auth-api.md.
 * Trạng thái lưu ở sessionStorage để giữ đăng nhập khi tải lại trang trong cùng tab.
 * Chỉ dùng tài khoản và mật khẩu mẫu, không dùng dữ liệu thật.
 */
import { AuthError, type LoginInput, type RegisterInput, type User } from './types';
import { normalizeEmail } from './validation';

export const MOCK_OTP = '123456';
export const MOCK_OTP_EXPIRED = '000000';
const OTP_MAX_ATTEMPTS = 5;
const OTP_TTL_MS = 5 * 60 * 1000;
const STORAGE_KEY = 'examind:mock-auth';

/** Kịch bản thử, hiện ở khung gợi ý trên trang đăng nhập khi bật mock. */
export const mockScenarios = [
  { label: 'Học sinh', email: 'hs01@example.com', password: 'hs01-demo', note: 'Đăng nhập thành công' },
  { label: 'Quản trị', email: 'admin@example.com', password: 'admin-demo-123', note: 'Chuyển tới /admin' },
  { label: 'Bị khoá', email: 'khoa@example.com', password: 'khoa-demo', note: 'Lỗi tài khoản bị khoá' },
  { label: 'Lỗi mạng', email: 'loimang@example.com', password: 'bat-ky', note: 'Giả lập mất kết nối' },
] as const;

interface MockAccount {
  password: string;
  user: User;
}

interface MockState {
  accounts: Record<string, MockAccount>;
  currentEmail: string | null;
  otp: { email: string; code: string; expiresAt: number; attempts: number } | null;
  resetToken: { email: string; token: string } | null;
}

/** Mật khẩu mẫu của tài khoản demo lấy từ `mockScenarios`, để chỉ khai báo một chỗ. */
const demoPassword = (email: string) => mockScenarios.find((s) => s.email === email)?.password ?? '';

const seedAccounts = (): Record<string, MockAccount> => ({
  'hs01@example.com': {
    password: demoPassword('hs01@example.com'),
    user: { user_id: 1, email: 'hs01@example.com', role: 'student', status: 'active', display_name: 'Học sinh 01', created_at: '2026-11-27T15:52:23.845134Z' },
  },
  'admin@example.com': {
    password: demoPassword('admin@example.com'),
    user: { user_id: 2, email: 'admin@example.com', role: 'admin', status: 'active', display_name: 'Quản trị', created_at: '2026-11-27T15:52:41.085593Z' },
  },
  'khoa@example.com': {
    password: demoPassword('khoa@example.com'),
    user: { user_id: 3, email: 'khoa@example.com', role: 'student', status: 'disabled', display_name: 'Tài khoản bị khoá', created_at: '2026-11-27T16:00:00.000000Z' },
  },
});

function load(): MockState {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as MockState;
  } catch {
    /* bỏ qua */
  }
  return { accounts: seedAccounts(), currentEmail: null, otp: null, resetToken: null };
}

function save(state: MockState) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* bỏ qua */
  }
}

const delay = (ms = 750) => new Promise((resolve) => window.setTimeout(resolve, ms));

function failIfNetwork(email: string) {
  if (normalizeEmail(email) === 'loimang@example.com') {
    throw new AuthError('NETWORK', 'Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại nhé.');
  }
}

export const mockAuthApi = {
  async login({ email, password }: LoginInput): Promise<User> {
    await delay();
    failIfNetwork(email);
    const state = load();
    const account = state.accounts[normalizeEmail(email)];
    if (!account || account.password !== password) {
      throw new AuthError('INVALID_CREDENTIALS', 'Email hoặc mật khẩu không đúng', 401);
    }
    if (account.user.status === 'disabled') {
      throw new AuthError('ACCOUNT_DISABLED', 'Tài khoản đã bị khoá', 403);
    }
    state.currentEmail = account.user.email;
    save(state);
    return account.user;
  },

  async register({ email, password, display_name }: RegisterInput): Promise<User> {
    await delay(900);
    failIfNetwork(email);
    const state = load();
    const key = normalizeEmail(email);
    if (state.accounts[key]) throw new AuthError('EMAIL_TAKEN', 'Email này đã được đăng ký', 409);
    const user: User = {
      user_id: Object.keys(state.accounts).length + 1,
      email: key,
      role: 'student',
      status: 'active',
      display_name: display_name?.trim() || null,
      created_at: new Date().toISOString(),
    };
    state.accounts[key] = { password, user };
    state.currentEmail = key;
    save(state);
    return user;
  },

  async logout(): Promise<void> {
    await delay(300);
    const state = load();
    state.currentEmail = null;
    save(state);
  },

  async me(): Promise<User> {
    await delay(250);
    const state = load();
    const account = state.currentEmail ? state.accounts[state.currentEmail] : undefined;
    if (!account) throw new AuthError('SESSION_MISSING', 'Chưa đăng nhập', 401);
    return account.user;
  },

  async forgotPassword(email: string): Promise<void> {
    await delay(900);
    failIfNetwork(email);
    const state = load();
    // Luôn trả thành công để không lộ email nào đã đăng ký. Chỉ tạo OTP khi email có thật.
    const key = normalizeEmail(email);
    state.otp = state.accounts[key] ? { email: key, code: MOCK_OTP, expiresAt: Date.now() + OTP_TTL_MS, attempts: 0 } : null;
    save(state);
  },

  async verifyOtp(email: string, code: string): Promise<{ reset_token: string }> {
    await delay(700);
    const state = load();
    const otp = state.otp;
    if (code === MOCK_OTP_EXPIRED || !otp || otp.email !== normalizeEmail(email) || otp.expiresAt < Date.now()) {
      throw new AuthError('OTP_EXPIRED', 'Mã xác minh đã hết hạn', 410);
    }
    if (otp.attempts >= OTP_MAX_ATTEMPTS) {
      throw new AuthError('TOO_MANY_ATTEMPTS', 'Bạn đã nhập sai quá nhiều lần', 429);
    }
    if (code !== otp.code) {
      otp.attempts += 1;
      save(state);
      const remaining = OTP_MAX_ATTEMPTS - otp.attempts;
      if (remaining <= 0) throw new AuthError('TOO_MANY_ATTEMPTS', 'Bạn đã nhập sai quá nhiều lần', 429);
      throw new AuthError('OTP_INVALID', 'Mã xác minh không đúng', 400, undefined, remaining);
    }
    const token = `mock-${Math.random().toString(36).slice(2)}`;
    state.otp = null;
    state.resetToken = { email: otp.email, token };
    save(state);
    return { reset_token: token };
  },

  async resetPassword(resetToken: string, password: string): Promise<void> {
    await delay(900);
    const state = load();
    if (!state.resetToken || state.resetToken.token !== resetToken) {
      throw new AuthError('RESET_TOKEN_INVALID', 'Phiên đặt lại mật khẩu không còn hiệu lực', 400);
    }
    const account = state.accounts[state.resetToken.email];
    if (account) account.password = password;
    state.resetToken = null;
    save(state);
  },
};
