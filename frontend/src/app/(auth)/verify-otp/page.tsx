import type { Metadata } from 'next';
import { VerifyOtpForm } from '@/features/auth/forms/verify-otp-form';

export const metadata: Metadata = { title: 'Nhập mã xác minh' };

export default function VerifyOtpPage() {
  return <VerifyOtpForm />;
}
