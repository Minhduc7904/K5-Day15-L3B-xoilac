import type { Metadata } from 'next';
import { LoginForm, type LoginReason } from '@/features/auth/forms/login-form';

export const metadata: Metadata = { title: 'Đăng nhập quản trị' };

const reasons: LoginReason[] = ['session-expired', 'logged-out'];

/** Đăng nhập cho quản trị viên. Phiên admin tách khỏi phiên học sinh nên đăng nhập ở đây không đăng xuất học sinh. */
export default async function AdminLoginPage({ searchParams }: { searchParams: Promise<{ reason?: string | string[] }> }) {
  const { reason } = await searchParams;
  const value = typeof reason === 'string' && (reasons as string[]).includes(reason) ? (reason as LoginReason) : undefined;
  return <LoginForm reason={value} variant="admin" />;
}
