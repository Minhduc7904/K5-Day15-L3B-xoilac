/** Kiểm dữ liệu phía client, bám ràng buộc của backend auth (PR #17). Backend vẫn kiểm lại. */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const RESERVED_TLDS = ['.local', '.test', '.invalid', '.localhost', '.example'];

export function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

export function validateEmail(raw: string): string | undefined {
  const email = normalizeEmail(raw);
  if (!email) return 'Bạn nhập email nhé.';
  if (email.length > 255) return 'Email dài tối đa 255 ký tự.';
  if (!EMAIL_RE.test(email) || RESERVED_TLDS.some((tld) => email.endsWith(tld))) {
    return 'Email chưa đúng định dạng, ví dụ ban@gmail.com.';
  }
  return undefined;
}

export function validateLoginPassword(password: string): string | undefined {
  if (!password) return 'Bạn nhập mật khẩu nhé.';
  if (password.length > 128) return 'Mật khẩu dài tối đa 128 ký tự.';
  return undefined;
}

export function validateNewPassword(password: string): string | undefined {
  if (!password) return 'Bạn đặt mật khẩu nhé.';
  if (password.length < 8) return 'Mật khẩu cần ít nhất 8 ký tự.';
  if (password.length > 128) return 'Mật khẩu dài tối đa 128 ký tự.';
  return undefined;
}

export function validateConfirm(password: string, confirm: string): string | undefined {
  if (!confirm) return 'Bạn nhập lại mật khẩu nhé.';
  if (password !== confirm) return 'Mật khẩu nhập lại chưa khớp.';
  return undefined;
}

export function validateDisplayName(name: string): string | undefined {
  if (name.trim().length > 100) return 'Tên hiển thị dài tối đa 100 ký tự.';
  return undefined;
}

export type PasswordStrength = 0 | 1 | 2 | 3 | 4;

/** Ước lượng độ mạnh để gợi ý, không phải luật bắt buộc. */
export function passwordStrength(password: string): PasswordStrength {
  if (!password) return 0;
  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[a-zA-Z]/.test(password) && /\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password) || /[A-Z]/.test(password)) score++;
  return Math.min(score, 4) as PasswordStrength;
}

/** h***@example.com — để hiện email đã gửi mã mà không lộ toàn bộ. */
export function maskEmail(email: string) {
  const [name, domain] = email.split('@');
  if (!domain) return email;
  return `${name.slice(0, 1)}${'*'.repeat(Math.max(2, Math.min(name.length - 1, 5)))}@${domain}`;
}
