import type { Metadata } from 'next';
import { ResetPasswordForm } from '@/features/auth/forms/reset-password-form';

export const metadata: Metadata = { title: 'Đặt mật khẩu mới' };

export default function ResetPasswordPage() {
  return <ResetPasswordForm />;
}
