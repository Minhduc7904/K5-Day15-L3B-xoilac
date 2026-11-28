import type { Metadata } from 'next';
import { GoogleCallback } from '@/features/auth/forms/google-callback';

export const metadata: Metadata = { title: 'Đăng nhập Google' };

export default function GoogleCallbackPage() {
  return <GoogleCallback />;
}
