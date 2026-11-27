'use client';

import { MotionConfig } from 'motion/react';
import { useState, type ReactNode } from 'react';
import { Provider } from 'react-redux';
import { SplashScreen } from '@/components/splash/splash-screen';
import { ToastProvider } from '@/components/ui/toast';
import { RealtimeBridge } from '@/features/realtime/use-realtime';
import { makeStore } from './index';

export function AppProvider({ children }: { children: ReactNode }) {
  const [store] = useState(makeStore);
  return (
    <Provider store={store}>
      {/* Tôn trọng cài đặt giảm chuyển động của hệ điều hành cho mọi hoạt ảnh motion. */}
      <MotionConfig reducedMotion="user">
        <ToastProvider>
          {/* Kết nối socket theo trạng thái đăng nhập (#20). Cần nằm trong ToastProvider và store. */}
          <RealtimeBridge />
          <SplashScreen>{children}</SplashScreen>
        </ToastProvider>
      </MotionConfig>
    </Provider>
  );
}
