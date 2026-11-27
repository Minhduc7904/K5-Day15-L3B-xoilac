import type { Metadata } from 'next';
import { ForgotPasswordForm } from '@/features/auth/forms/forgot-password-form';

export const metadata: Metadata = { title: 'Quên mật khẩu' };

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
