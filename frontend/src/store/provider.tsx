'use client';

import { MotionConfig } from 'motion/react';
import { useState, type ReactNode } from 'react';
import { Provider } from 'react-redux';
import { SplashScreen } from '@/components/splash/splash-screen';
import { ToastProvider } from '@/components/ui/toast';
import { makeStore } from './index';

export function AppProvider({ children }: { children: ReactNode }) {
  const [store] = useState(makeStore);
  return (
    <Provider store={store}>
      {/* Tôn trọng cài đặt giảm chuyển động của hệ điều hành cho mọi hoạt ảnh motion. */}
      <MotionConfig reducedMotion="user">
        <ToastProvider>
          <SplashScreen>{children}</SplashScreen>
        </ToastProvider>
      </MotionConfig>
    </Provider>
  );
}
