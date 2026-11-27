import type { ReactNode } from 'react';
import { Container } from '@/components/layout/container';
import { Logo } from '@/components/layout/logo';
import { UserMenu } from '@/features/auth/components/user-menu';

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="border-b border-border bg-background">
        <Container size="full" className="flex h-16 items-center gap-2">
          <Logo href="/admin" priority />
          <div className="ml-auto flex items-center gap-2">
            <UserMenu />
          </div>
        </Container>
      </header>
      {children}
    </>
  );
}
