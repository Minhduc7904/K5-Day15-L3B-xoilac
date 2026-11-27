import type { ReactNode } from 'react';
import { AppShell } from '@/features/study/components/app-shell';

export default function StudentAppLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
