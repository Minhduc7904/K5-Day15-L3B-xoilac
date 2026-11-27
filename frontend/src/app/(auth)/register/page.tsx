import type { Metadata } from 'next';
import { RegisterForm } from '@/features/auth/forms/register-form';

export const metadata: Metadata = { title: 'Tạo tài khoản' };

export default function RegisterPage() {
  return <RegisterForm />;
}
