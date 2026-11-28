'use client';

import { LogIn, Mail, RotateCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { useToast } from '@/components/ui/toast';
import { useAppDispatch } from '@/store';
import { authApi } from '../api';
import { signedInAs } from '../auth-slice';
import { homeFor } from '../route-guard';
import { AuthHeader, AuthSwitch, TextLink } from '../components/auth-shell';
import { GoogleSignIn } from '../components/google-sign-in';
import { toAuthError, type AuthErrorCode } from '../types';
import { useAuthForm } from '../use-auth-form';
import { normalizeEmail, validateEmail, validateLoginPassword } from '../validation';

export type LoginReason = 'session-expired' | 'password-reset' | 'logged-out';

const reasonAlerts: Record<LoginReason, { tone: 'info' | 'success'; title: string; body: string }> = {
  'session-expired': {
    tone: 'info',
    title: 'Phiên đăng nhập đã hết hạn',
    body: 'Bạn đăng nhập lại để tiếp tục nhé.',
  },
  'password-reset': {
    tone: 'success',
    title: 'Đã đổi mật khẩu',
    body: 'Đăng nhập bằng mật khẩu mới của bạn.',
  },
  'logged-out': { tone: 'info', title: 'Bạn đã đăng xuất', body: 'Hẹn gặp lại bạn ở buổi ôn tiếp theo.' },
};

const errorAlerts: Partial<Record<AuthErrorCode, { tone: 'danger' | 'warning'; title: string; body: string }>> = {
  INVALID_CREDENTIALS: {
    tone: 'danger',
    title: 'Email hoặc mật khẩu không đúng',
    body: 'Kiểm tra lại, chú ý chữ hoa và bộ gõ tiếng Việt khi nhập mật khẩu.',
  },
  ACCOUNT_DISABLED: {
    tone: 'warning',
    title: 'Tài khoản đã bị khoá',
    body: 'Bạn chưa đăng nhập được bằng tài khoản này. Liên hệ thầy cô hoặc quản trị viên để được mở khoá.',
  },
  NETWORK: {
    tone: 'danger',
    title: 'Không kết nối được máy chủ',
    body: 'Kiểm tra kết nối mạng rồi thử lại nhé.',
  },
};

/** `admin`: trang /login/admin cho quản trị viên, không có Google, đăng ký và quên mật khẩu (chỉ dành cho học sinh). */
export function LoginForm({ reason, variant = 'student' }: { reason?: LoginReason; variant?: 'student' | 'admin' }) {
  const isAdmin = variant === 'admin';
  const router = useRouter();
  const dispatch = useAppDispatch();
  const toast = useToast();
  const [failure, setFailure] = useState<AuthErrorCode | null>(null);

  const form = useAuthForm({ email: '', password: '' }, (v) => ({
    email: validateEmail(v.email),
    password: validateLoginPassword(v.password),
  }));

  const submit = form.handleSubmit(async ({ email, password }) => {
    setFailure(null);
    try {
      const user = await authApi.login({ email: normalizeEmail(email), password });
      dispatch(signedInAs(user));
      toast({ tone: 'success', title: `Chào ${user.display_name ?? 'bạn'}!`, description: 'Đăng nhập thành công.' });
      router.replace(homeFor(user));
    } catch (error) {
      const authError = toAuthError(error);
      if (authError.code === 'VALIDATION' && authError.fieldErrors) {
        form.setServerErrors(authError.fieldErrors);
      } else {
        setFailure(errorAlerts[authError.code] ? authError.code : 'NETWORK');
      }
    }
  });

  const alert = failure ? errorAlerts[failure] : reason ? reasonAlerts[reason] : undefined;

  return (
    <div className="grid gap-7">
      <AuthHeader
        icon={<LogIn />}
        mascot="welcome"
        title={isAdmin ? 'Đăng nhập quản trị' : 'Đăng nhập'}
        description={
          isAdmin
            ? 'Dành cho quản trị viên. Phiên này tách riêng với tài khoản học sinh của bạn.'
            : 'Chào bạn quay lại! Đăng nhập để tiếp tục ôn tập.'
        }
      />

      {alert && (
        <Alert
          key={failure ?? reason}
          tone={alert.tone}
          title={alert.title}
          action={
            failure === 'NETWORK' ? (
              <Button size="sm" variant="outline" leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => submit()} loading={form.submitting}>
                Thử lại
              </Button>
            ) : undefined
          }
        >
          {alert.body}
        </Alert>
      )}

      <form ref={form.formRef} noValidate onSubmit={submit} className="grid gap-5">
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

        <div className="grid gap-1.5">
          <FormField label="Mật khẩu" required error={form.errors.password}>
            {(field) => (
              <PasswordInput
                {...field}
                name="password"
                autoComplete="current-password"
                placeholder="Nhập mật khẩu"
                value={form.values.password}
                onChange={(e) => form.setField('password', e.target.value)}
              />
            )}
          </FormField>
          {!isAdmin && (
            <div className="flex justify-end">
              <TextLink href="/forgot-password">Quên mật khẩu?</TextLink>
            </div>
          )}
        </div>

        <Button type="submit" size="lg" fullWidth loading={form.submitting}>
          {form.submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
      </form>

      {isAdmin ? (
        <AuthSwitch question="Không phải quản trị viên?" href="/login" label="Đăng nhập học sinh" />
      ) : (
        <>
          <GoogleSignIn />
          <AuthSwitch question="Chưa có tài khoản?" href="/register" label="Tạo tài khoản" />
        </>
      )}
    </div>
  );
}
