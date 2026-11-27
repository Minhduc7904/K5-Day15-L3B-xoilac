import type { ReactNode } from 'react';
import { StudentHeader } from './student-header';

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-surface [--student-header-height:3.75rem] lg:[--student-header-height:4rem]">
      <a
        href="#noi-dung"
        className="sr-only z-50 rounded-xl bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Bỏ qua tới nội dung chính
      </a>
      <StudentHeader />
      <main
        id="noi-dung"
        tabIndex={-1}
        className="min-w-0 scroll-mt-[var(--student-header-height)] outline-none"
      >
        {children}
      </main>
    </div>
  );
}
