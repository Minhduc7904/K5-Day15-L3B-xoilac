/**
 * Cờ "đã xem hướng dẫn" theo từng tài khoản. Đổi `VERSION` khi nội dung tour thay đổi đủ nhiều
 * để người đã xem nên xem lại. Khoá này là lựa chọn của người dùng nên không bị dọn cùng các khoá dữ liệu cũ.
 */
const VERSION = 'v1';

export type OnboardingResult = 'completed' | 'skipped';

type UserId = string | number;

const keyFor = (userId: UserId) => `examind:onboarding:${VERSION}:${userId}`;

export function readOnboarding(userId: UserId): OnboardingResult | null {
  try {
    const value = window.localStorage.getItem(keyFor(userId));
    return value === 'completed' || value === 'skipped' ? value : null;
  } catch {
    return null;
  }
}

export function writeOnboarding(userId: UserId, result: OnboardingResult) {
  try {
    window.localStorage.setItem(keyFor(userId), result);
  } catch {
    /* trình duyệt chặn storage: tour chỉ không nhớ được lần sau */
  }
}
