'use client';

import { MotionConfig } from 'motion/react';
import { useEffect, useState, type ReactNode } from 'react';
import { Provider } from 'react-redux';
import { SplashScreen } from '@/components/splash/splash-screen';
import { ToastProvider } from '@/components/ui/toast';
import { signedOut } from '@/features/auth/auth-slice';
import { AuthGuard } from '@/features/auth/route-guard';
import { onSessionLost } from '@/lib/api-client';
import { makeStore } from './index';

export function AppProvider({ children }: { children: ReactNode }) {
  const [store] = useState(makeStore);

  // API nào báo mất phiên (hết hạn, bị thu hồi, tài khoản bị khoá) thì đăng xuất phía client.
  useEffect(
    () =>
      onSessionLost(() => {
        if (store.getState().auth.user) store.dispatch(signedOut('session-expired'));
      }),
    [store],
  );
  return (
    <Provider store={store}>
      {/* Tôn trọng cài đặt giảm chuyển động của hệ điều hành cho mọi hoạt ảnh motion. */}
      <MotionConfig reducedMotion="user">
        <ToastProvider>
          <SplashScreen>
            <AuthGuard>{children}</AuthGuard>
          </SplashScreen>
        </ToastProvider>
      </MotionConfig>
    </Provider>
  );
}
