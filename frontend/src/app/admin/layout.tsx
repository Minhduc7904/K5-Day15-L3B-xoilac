import type { ReactNode } from 'react';
import { Container } from '@/components/layout/container';
import { Logo } from '@/components/layout/logo';

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="border-b border-border bg-background">
        <Container size="full" className="flex h-16 items-center">
          <Logo href="/admin" priority />
        </Container>
      </header>
      {children}
    </>
  );
}
