import type { Metadata } from 'next';
import { LoginForm, type LoginReason } from '@/features/auth/forms/login-form';

export const metadata: Metadata = { title: 'Đăng nhập' };

const reasons: LoginReason[] = ['session-expired', 'password-reset', 'logged-out'];

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ reason?: string | string[] }> }) {
  const { reason } = await searchParams;
  const value = typeof reason === 'string' && (reasons as string[]).includes(reason) ? (reason as LoginReason) : undefined;
  return <LoginForm reason={value} />;
}
