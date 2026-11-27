import type { ReactNode } from 'react';
import { Logo } from '@/components/layout/logo';
import { AuthAside } from '@/features/auth/components/auth-aside';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <AuthAside />
      <div className="relative flex min-w-0 flex-col">
        <div className="bg-grid mask-fade pointer-events-none absolute inset-0 lg:hidden" aria-hidden="true" />
        <header className="relative flex h-16 items-center px-4 sm:h-18 sm:px-8">
          <Logo href="/login" />
        </header>
        <main id="noi-dung" className="relative flex flex-1 items-start justify-center px-4 py-8 sm:items-center sm:px-8 sm:py-12">
          <div className="w-full max-w-[440px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
