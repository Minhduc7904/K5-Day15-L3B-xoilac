'use client';

import { MotionConfig } from 'motion/react';
import { useEffect, useState, type ReactNode } from 'react';
import { Provider } from 'react-redux';
import { SplashScreen } from '@/components/splash/splash-screen';
import { ToastProvider } from '@/components/ui/toast';
import { authOf, signedOutOf } from '@/features/auth/auth-slice';
import { AuthGuard } from '@/features/auth/route-guard';
import { RealtimeConnection } from '@/features/realtime/realtime-connection';
import { StudentAccountProvider } from '@/features/study/profile/student-account-provider';
import { onSessionLost } from '@/lib/api-client';
import { makeStore } from './index';

export function AppProvider({ children }: { children: ReactNode }) {
  const [store] = useState(makeStore);

  // API nào báo mất phiên (hết hạn, bị thu hồi, tài khoản bị khoá) thì đăng xuất phía client.
  useEffect(
    () =>
      onSessionLost((scope) => {
        if (authOf(store.getState(), scope).user) store.dispatch(signedOutOf(scope, 'session-expired'));
      }),
    [store],
  );
  return (
    <Provider store={store}>
      <RealtimeConnection />
      {/* Tôn trọng cài đặt giảm chuyển động của hệ điều hành cho mọi hoạt ảnh motion. */}
      <MotionConfig reducedMotion="user">
        <ToastProvider>
          <SplashScreen>
            <AuthGuard><StudentAccountProvider>{children}</StudentAccountProvider></AuthGuard>
          </SplashScreen>
        </ToastProvider>
      </MotionConfig>
    </Provider>
  );
}
