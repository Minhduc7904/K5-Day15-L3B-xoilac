/**
 * Các bước khởi động app, chạy lần lượt sau splash screen.
 * Thêm bước mới (cấu hình từ server…) vào `bootstrapSteps`.
 * Mỗi bước có giới hạn thời gian để splash không bao giờ treo.
 */
import { authApi } from '@/features/auth/api';
import { sessionChecked } from '@/features/auth/auth-slice';
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

export const bootstrapSteps: BootstrapStep[] = [
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
    // Gọi GET /auth/me qua lớp API của feature auth (đang mock khi bật NEXT_PUBLIC_MOCK_MODE).
    run: async ({ dispatch }) => {
      try {
        dispatch(sessionChecked(await authApi.me()));
      } catch {
        dispatch(sessionChecked(null));
      }
    },
  },
];

export function withTimeout(promise: Promise<void>, ms = STEP_TIMEOUT_MS) {
  return Promise.race([promise, new Promise<void>((resolve) => window.setTimeout(resolve, ms))]);
}

export const wait = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));
