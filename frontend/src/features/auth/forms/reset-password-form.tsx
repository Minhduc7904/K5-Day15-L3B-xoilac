'use client';

import { LockKeyhole, RotateCcw } from 'lucide-react';
import Image from 'next/image';
import { motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { PasswordInput } from '@/components/ui/password-input';
import { authApi } from '../api';
import { AuthHeader } from '../components/auth-shell';
import { PasswordStrength } from '../components/password-strength';
import { clearResetFlow, readResetFlow, type ResetFlow } from '../reset-flow';
import { toAuthError } from '../types';
import { useAuthForm } from '../use-auth-form';
import { validateConfirm, validateNewPassword } from '../validation';

export function ResetPasswordForm() {
  const [flow, setFlow] = useState<ResetFlow | null | undefined>(undefined);
  const [done, setDone] = useState(false);
  const [failure, setFailure] = useState<'token' | 'network' | null>(null);

  useEffect(() => setFlow(readResetFlow()), []);

  const form = useAuthForm({ password: '', confirm: '' }, (v) => ({
    password: validateNewPassword(v.password),
    confirm: validateConfirm(v.password, v.confirm),
  }));

  const submit = form.handleSubmit(async ({ password }) => {
    if (!flow?.resetToken) return;
    setFailure(null);
    try {
      await authApi.resetPassword(flow.resetToken, password);
      clearResetFlow();
      setDone(true);
    } catch (error) {
      const authError = toAuthError(error);
      if (authError.code === 'RESET_TOKEN_INVALID') {
        clearResetFlow();
        setFailure('token');
      } else if (authError.code === 'VALIDATION' && authError.fieldErrors) {
        form.setServerErrors({ password: authError.fieldErrors.password });
      } else {
        setFailure('network');
      }
    }
  });

  if (flow === undefined) {
    return (
      <div className="grid gap-4" aria-hidden="true">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  if (done) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="grid justify-items-center gap-5 text-center"
        role="status"
      >
        <motion.div initial={{ y: 20 }} animate={{ y: [20, -8, 0] }} transition={{ duration: 0.6 }}>
          <Image src="/brand/mascot/static/success.webp" alt="" width={384} height={384} className="h-auto w-40" />
        </motion.div>
        <h1 className="text-h1 text-foreground">Đổi mật khẩu thành công!</h1>
        <p className="text-body text-muted-foreground">Từ giờ bạn đăng nhập bằng mật khẩu mới nhé.</p>
        <Button href="/login?reason=password-reset" size="lg" fullWidth>
          Đăng nhập
        </Button>
      </motion.div>
    );
  }

  if (!flow?.resetToken || failure === 'token') {
    return (
      <div className="grid gap-7">
        <AuthHeader icon={<LockKeyhole />} mascot="studying" title="Đặt mật khẩu mới" description="Bạn cần xác minh email trước đã." />
        <Alert
          tone="warning"
          title="Phiên đặt lại mật khẩu không còn hiệu lực"
          action={
            <Button size="sm" href="/forgot-password">
              Bắt đầu lại
            </Button>
          }
        >
          Có thể bạn chưa nhập mã xác minh, hoặc đã dùng phiên này để đổi mật khẩu rồi.
        </Alert>
      </div>
    );
  }

  return (
    <div className="grid gap-7">
      <AuthHeader
        icon={<LockKeyhole />}
        mascot="studying"
        title="Đặt mật khẩu mới"
        description="Chọn mật khẩu bạn chưa dùng ở nơi khác để an toàn hơn."
      />

      {failure === 'network' && (
        <Alert
          tone="danger"
          title="Chưa đổi được mật khẩu"
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
        {/* Giúp trình quản lý mật khẩu lưu đúng tài khoản. */}
        <input type="email" name="email" autoComplete="username" value={flow.email} readOnly hidden />

        <div className="grid gap-2">
          <FormField label="Mật khẩu mới" required hint="Từ 6 đến 128 ký tự." error={form.errors.password}>
            {(field) => (
              <PasswordInput
                {...field}
                name="new-password"
                autoComplete="new-password"
                placeholder="Tạo mật khẩu mới"
                value={form.values.password}
                onChange={(e) => form.setField('password', e.target.value)}
                autoFocus
                data-autofocus
              />
            )}
          </FormField>
          <PasswordStrength password={form.values.password} />
        </div>

        <FormField label="Nhập lại mật khẩu mới" required error={form.errors.confirm}>
          {(field) => (
            <PasswordInput
              {...field}
              name="confirm-password"
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu mới"
              value={form.values.confirm}
              onChange={(e) => form.setField('confirm', e.target.value)}
            />
          )}
        </FormField>

        <Button type="submit" size="lg" fullWidth loading={form.submitting}>
          {form.submitting ? 'Đang lưu…' : 'Lưu mật khẩu mới'}
        </Button>
      </form>
    </div>
  );
}
