'use client';

/** Đặt lại mật khẩu cho một tài khoản (#20). Backend thu hồi mọi phiên và ngắt socket của người đó. */
import { useEffect, useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Modal } from '@/components/ui/modal';
import { PasswordInput } from '@/components/ui/password-input';
import { toApiError } from '@/lib/api-error';
import { adminUsersApi } from '../api';
import { PASSWORD_MAX, PASSWORD_MIN, type AdminUser } from '../types';

interface Props {
  user: AdminUser | null;
  onClose: () => void;
  onDone: (user: AdminUser) => void;
}

export function ResetPasswordModal({ user, onClose, onDone }: Props) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setPassword('');
    setError(null);
  }, [user]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
      setError(`Mật khẩu cần từ ${PASSWORD_MIN} đến ${PASSWORD_MAX} ký tự.`);
      return;
    }
    setSaving(true);
    try {
      await adminUsersApi.resetPassword(user.user_id, password);
      onDone(user);
    } catch (err) {
      const apiError = toApiError(err);
      setError(apiError.fieldErrors?.password ?? apiError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={user !== null}
      onClose={onClose}
      title="Đặt lại mật khẩu"
      description={user ? `${user.email} sẽ bị đăng xuất khỏi mọi thiết bị.` : undefined}
    >
      <form className="grid gap-4" onSubmit={submit} noValidate>
        <FormField label="Mật khẩu mới" required error={error ?? undefined} hint={`${PASSWORD_MIN}–${PASSWORD_MAX} ký tự`}>
          {(f) => <PasswordInput {...f} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />}
        </FormField>
        <Alert tone="info" title="Gửi mật khẩu mới cho người dùng qua kênh riêng, không dán vào nhóm chat chung." />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Huỷ
          </Button>
          <Button type="submit" variant="danger" loading={saving}>
            Đặt lại
          </Button>
        </div>
      </form>
    </Modal>
  );
}
