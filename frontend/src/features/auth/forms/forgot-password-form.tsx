'use client';

import { KeyRound, Mail, RotateCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { mockMode } from '@/lib/config';
import { authApi } from '../api';
import { AuthHeader, AuthSwitch, MockNote } from '../components/auth-shell';
import { MOCK_OTP } from '../mock';
import { readResetFlow, writeResetFlow } from '../reset-flow';
import { toAuthError } from '../types';
import { useAuthForm } from '../use-auth-form';
import { normalizeEmail, validateEmail } from '../validation';

export function ForgotPasswordForm() {
  const router = useRouter();
  const toast = useToast();
  const [networkError, setNetworkError] = useState(false);

  const form = useAuthForm({ email: '' }, (v) => ({ email: validateEmail(v.email) }));

  // Quay lại từ bước nhập mã ("Đổi email khác") thì điền sẵn email cũ.
  useEffect(() => {
    const pending = readResetFlow();
    if (pending) form.setField('email', pending.email);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = form.handleSubmit(async ({ email }) => {
    setNetworkError(false);
    const normalized = normalizeEmail(email);
    try {
      await authApi.forgotPassword(normalized);
      writeResetFlow({ email: normalized, sentAt: Date.now() });
      toast({
        tone: 'success',
        title: 'Đã gửi mã xác minh',
        description: mockMode ? `Mock: mã của bạn là ${MOCK_OTP}.` : 'Kiểm tra hộp thư, kể cả mục Spam.',
      });
      router.push('/verify-otp');
    } catch (error) {
      const authError = toAuthError(error);
      if (authError.code === 'VALIDATION') form.setServerErrors({ email: 'Email chưa đúng định dạng.' });
      else setNetworkError(true);
    }
  });

  return (
    <div className="grid gap-7">
      <AuthHeader
        icon={<KeyRound />}
        mascot="studying"
        title="Quên mật khẩu"
        description="Nhập email bạn đã đăng ký. Mình sẽ gửi mã xác minh 6 số để bạn đặt lại mật khẩu."
      />

      {networkError && (
        <Alert
          tone="danger"
          title="Chưa gửi được mã"
          action={
            <Button size="sm" variant="outline" leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => submit()} loading={form.submitting}>
              Thử lại
            </Button>
          }
        >
          Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại nhé.
        </Alert>
      )}

      <form ref={form.formRef} noValidate onSubmit={submit} className="grid gap-5">
        <FormField
          label="Email"
          required
          hint="Nếu email này đã đăng ký, bạn sẽ nhận được mã trong vài phút."
          error={form.errors.email}
        >
          {(field) => (
            <Input
              {...field}
              name="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder="ban@gmail.com"
              leftIcon={<Mail />}
              value={form.values.email}
              onChange={(e) => form.setField('email', e.target.value)}
            />
          )}
        </FormField>

        <Button type="submit" size="lg" fullWidth loading={form.submitting}>
          {form.submitting ? 'Đang gửi mã…' : 'Gửi mã xác minh'}
        </Button>
      </form>

      <AuthSwitch question="Nhớ ra mật khẩu rồi?" href="/login" label="Đăng nhập" />

      <MockNote>
        Dùng <code>hs01@example.com</code> để nhận mã thật trong mock. Email chưa đăng ký vẫn báo đã gửi (để không lộ tài
        khoản) nhưng mã sẽ không dùng được.
      </MockNote>
    </div>
  );
}
