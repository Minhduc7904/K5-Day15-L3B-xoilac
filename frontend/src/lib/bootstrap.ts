/**
 * Các bước khởi động app, chạy lần lượt sau splash screen.
 * Thêm bước mới (cấu hình từ server…) vào `bootstrapSteps`.
 * Mỗi bước có giới hạn thời gian để splash không bao giờ treo.
 */
import { authApi } from '@/features/auth/api';
import { sessionCheckedOf } from '@/features/auth/auth-slice';
import type { AuthScope } from '@/lib/auth-scope';
import type { AppDispatch } from '@/store';

export interface BootstrapContext {
  dispatch: AppDispatch;
}

export interface BootstrapStep {
  id: string;
  label: string;
  run: (ctx: BootstrapContext) => Promise<void>;
}

const STEP_TIMEOUT_MS = 4000;

function preloadImage(src: string) {
  return new Promise<void>((resolve) => {
    const img = new window.Image();
    img.onload = () => resolve();
    img.onerror = () => resolve();
    img.src = src;
  });
}

/** Khoá localStorage của bản dùng dữ liệu mẫu cũ. Dữ liệu thật nằm ở server nên các khoá này không còn tác dụng. */
const STALE_KEYS = ['examind:mock-study', 'examind:chat-sessions:v1', 'examind:mock-auth'];
const STALE_PREFIXES = ['examind:attempt-draft:'];

function clearStaleStorage() {
  try {
    const keys = Array.from({ length: window.localStorage.length }, (_, i) => window.localStorage.key(i) ?? '');
    for (const key of keys) {
      if (STALE_KEYS.includes(key) || STALE_PREFIXES.some((prefix) => key.startsWith(prefix))) window.localStorage.removeItem(key);
    }
  } catch {
    // Không đọc được localStorage (chế độ riêng tư): bỏ qua.
  }
}

export const bootstrapSteps: BootstrapStep[] = [
  {
    id: 'storage',
    label: 'Dọn dữ liệu cũ',
    run: async () => clearStaleStorage(),
  },
  {
    id: 'fonts',
    label: 'Tải phông chữ',
    run: async () => {
      if ('fonts' in document) await document.fonts.ready;
    },
  },
  {
    id: 'assets',
    label: 'Chuẩn bị hình ảnh',
    run: async () => {
      await Promise.all(
        ['/brand/mascot/static/welcome.webp', '/brand/mascot/thinking/loop.webp'].map(preloadImage),
      );
    },
  },
  {
    id: 'session',
    label: 'Kiểm tra phiên đăng nhập',
    // Gọi GET /auth/me qua lớp API của feature auth, cho cả hai phiên (học sinh và admin) song song.
    run: async ({ dispatch }) => {
      const scopes: AuthScope[] = ['student', 'admin'];
      await Promise.all(
        scopes.map(async (scope) => {
          try {
            dispatch(sessionCheckedOf(scope, await authApi.me(scope)));
          } catch {
            dispatch(sessionCheckedOf(scope, null));
          }
        }),
      );
    },
  },
];

export function withTimeout(promise: Promise<void>, ms = STEP_TIMEOUT_MS) {
  return Promise.race([promise, new Promise<void>((resolve) => window.setTimeout(resolve, ms))]);
}

export const wait = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));
