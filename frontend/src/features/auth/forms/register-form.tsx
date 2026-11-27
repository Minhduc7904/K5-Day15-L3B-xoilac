'use client';

import { Mail, RotateCcw, UserPlus, UserRound } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { authApi } from '../api';
import { AuthHeader, AuthSwitch, MockNote } from '../components/auth-shell';
import { GoogleSignIn } from '../components/google-sign-in';
import { PasswordStrength } from '../components/password-strength';
import { toAuthError, type PendingOtp } from '../types';
import { useAuthForm } from '../use-auth-form';
import { normalizeEmail, validateConfirm, validateDisplayName, validateEmail, validateNewPassword } from '../validation';

import { EmailOtpForm } from './email-otp-form';

export function RegisterForm() {
  const [pending, setPending] = useState<PendingOtp>();
  const [failure, setFailure] = useState<ReturnType<typeof toAuthError>>();

  const form = useAuthForm(
    { displayName: '', email: '', password: '', confirm: '', agree: false as boolean },
    (v) => ({
      displayName: validateDisplayName(v.displayName),
      email: validateEmail(v.email),
      password: validateNewPassword(v.password),
      confirm: validateConfirm(v.password, v.confirm),
      agree: v.agree ? undefined : 'Bạn cần xác nhận điều này để tiếp tục.',
    }),
  );

  const submit = form.handleSubmit(async ({ displayName, email, password }) => {
    setFailure(undefined);
    try {
      const verification = await authApi.register({
        email: normalizeEmail(email),
        password,
        display_name: displayName.trim() || undefined,
      });
      form.patch({ password: '', confirm: '' });
      setPending(verification);
    } catch (error) {
      const authError = toAuthError(error);
      if (authError.code === 'EMAIL_TAKEN') {
        setFailure(authError);
        form.setServerErrors({ email: 'Email này đã được đăng ký.' });
      } else if (authError.code === 'VALIDATION' && authError.fieldErrors) {
        form.setServerErrors({
          email: authError.fieldErrors.email,
          password: authError.fieldErrors.password,
          displayName: authError.fieldErrors.display_name,
        });
      } else {
        setFailure(authError);
      }
    }
  });

  if (pending) {
    return <EmailOtpForm initial={pending} purpose="registration" onBack={() => setPending(undefined)} />;
  }

  return (
    <div className="grid gap-7">
      <AuthHeader
        icon={<UserPlus />}
        mascot="success"
        title="Tạo tài khoản"
        description="Tài khoản học sinh để nhận đề ôn theo chương bạn còn yếu."
      />

      {failure?.code === 'EMAIL_TAKEN' && (
        <Alert
          tone="info"
          title="Email này đã có tài khoản"
          action={
            <Button size="sm" variant="outline" href="/login">
              Đăng nhập
            </Button>
          }
        >
          Bạn có thể đăng nhập bằng email này.
        </Alert>
      )}
      {failure && failure.code !== 'EMAIL_TAKEN' && (
        <Alert
          tone="danger"
          title={failure.message}
          action={
            <Button size="sm" variant="outline" leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => submit()} loading={form.submitting}>
              Thử lại
            </Button>
          }
        />
      )}

      <form ref={form.formRef} noValidate onSubmit={submit} className="grid gap-5">
        <FormField label="Tên hiển thị" hint="Không bắt buộc. Examind dùng tên này để chào bạn." error={form.errors.displayName}>
          {(field) => (
            <Input
              {...field}
              name="name"
              autoComplete="nickname"
              placeholder="Ví dụ: Minh Anh"
              leftIcon={<UserRound />}
              value={form.values.displayName}
              onChange={(e) => form.setField('displayName', e.target.value)}
            />
          )}
        </FormField>

        <FormField label="Email" required error={form.errors.email}>
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

        <div className="grid gap-2">
          <FormField label="Mật khẩu" required hint="Từ 8 đến 128 ký tự." error={form.errors.password}>
            {(field) => (
              <PasswordInput
                {...field}
                name="new-password"
                autoComplete="new-password"
                placeholder="Tạo mật khẩu"
                value={form.values.password}
                onChange={(e) => form.setField('password', e.target.value)}
              />
            )}
          </FormField>
          <PasswordStrength password={form.values.password} />
        </div>

        <FormField label="Nhập lại mật khẩu" required error={form.errors.confirm}>
          {(field) => (
            <PasswordInput
              {...field}
              name="confirm-password"
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu"
              value={form.values.confirm}
              onChange={(e) => form.setField('confirm', e.target.value)}
            />
          )}
        </FormField>

        <div className="grid gap-1.5">
          <Checkbox
            name="agree"
            checked={form.values.agree}
            onChange={(e) => form.setField('agree', e.target.checked)}
            invalid={Boolean(form.errors.agree)}
            aria-describedby={form.errors.agree ? 'agree-error' : undefined}
            label="Mình hiểu đề do Examind tạo là đề luyện tập"
            description="Không phải đề hay điểm chính thức của trường."
          />
          {form.errors.agree && (
            <p id="agree-error" className="pl-8 text-caption font-medium text-danger">
              {form.errors.agree}
            </p>
          )}
        </div>

        <Button type="submit" size="lg" fullWidth loading={form.submitting}>
          {form.submitting ? 'Đang gửi mã…' : 'Gửi mã xác minh'}
        </Button>
      </form>

      <GoogleSignIn />

      <AuthSwitch question="Đã có tài khoản?" href="/login" label="Đăng nhập" />

      <MockNote>
        Email <code>hs01@example.com</code> đã có sẵn để thử lỗi trùng email. <code>loimang@example.com</code> giả lập
        mất mạng.
      </MockNote>
    </div>
  );
}
