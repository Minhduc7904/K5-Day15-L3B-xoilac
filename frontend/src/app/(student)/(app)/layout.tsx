import type { ReactNode } from 'react';
import { TourProvider } from '@/features/onboarding/tour-provider';
import { AppShell } from '@/features/study/components/app-shell';

export default function StudentAppLayout({ children }: { children: ReactNode }) {
  return (
    <TourProvider>
      <AppShell>{children}</AppShell>
    </TourProvider>
  );
}
