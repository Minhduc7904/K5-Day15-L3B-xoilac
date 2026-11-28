'use client';

/** Hộp thoại tạo hoặc sửa tài khoản (#20). Chỉ hiện trường mà người đang thao tác được phép đổi. */
import { useEffect, useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { fieldBase, fieldState, Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { PasswordInput } from '@/components/ui/password-input';
import { cn } from '@/lib/cn';
import { toApiError } from '@/lib/api-error';
import { adminUsersApi } from '../api';
import { canManage, type Principal } from '../permissions';
import { PASSWORD_MAX, PASSWORD_MIN, type AdminUser, type Role, type UpdateUserInput } from '../types';

interface Props {
  open: boolean;
  actor: Principal;
  /** null: tạo mới. */
  user: AdminUser | null;
  onClose: () => void;
  onSaved: (user: AdminUser) => void;
}

export const selectClass = cn(fieldBase, fieldState(false), 'h-11 px-3');

export function UserFormModal({ open, actor, user, onClose, onSaved }: Props) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<Role>('student');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setEmail(user?.email ?? '');
    setName(user?.display_name ?? '');
    setRole(user?.role ?? 'student');
    setPassword('');
    setErrors({});
    setFormError(null);
  }, [open, user]);

  // Trường nào người thao tác không đổi được thì khoá (backend vẫn kiểm lại).
  const canEdit = (changes: UpdateUserInput) => canManage(actor, user, user ? 'update' : 'create', changes) === null;
  const canChooseAdmin = user ? canEdit({ role: user.role === 'admin' ? 'student' : 'admin' }) : actor.is_root;
  const canEditEmail = !user || canEdit({ email: 'x@example.com' });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!user && (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX)) {
      nextErrors.password = `Mật khẩu cần từ ${PASSWORD_MIN} đến ${PASSWORD_MAX} ký tự.`;
    }
    if (!email.trim()) nextErrors.email = 'Nhập email.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setSaving(true);
    setFormError(null);
    try {
      if (!user) {
        onSaved(await adminUsersApi.create({ email, password, role, display_name: name || undefined }));
      } else {
        const changes: UpdateUserInput = {};
        if ((name || null) !== user.display_name) changes.display_name = name || null;
        if (email.trim().toLowerCase() !== user.email) changes.email = email;
        if (role !== user.role) changes.role = role;
        onSaved(Object.keys(changes).length ? await adminUsersApi.update(user.user_id, changes) : user);
      }
    } catch (err) {
      const apiError = toApiError(err);
      if (apiError.fieldErrors) setErrors(apiError.fieldErrors);
      else if (apiError.code === 'EMAIL_TAKEN') setErrors({ email: apiError.message });
      else setFormError(apiError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={user ? 'Sửa tài khoản' : 'Tạo tài khoản'}
      description={user ? user.email : 'Học sinh mới đăng nhập được ngay bằng mật khẩu bạn đặt.'}
    >
      <form className="grid gap-4" onSubmit={submit} noValidate>
        {formError && <Alert tone="danger" title={formError} />}
        <FormField label="Email" required error={errors.email}>
          {(f) => (
            <Input {...f} type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={!canEditEmail} autoComplete="off" />
          )}
        </FormField>
        <FormField label="Tên hiển thị" error={errors.display_name}>
          {(f) => <Input {...f} value={name} maxLength={100} onChange={(e) => setName(e.target.value)} />}
        </FormField>
        {!user && (
          <FormField label="Mật khẩu" required error={errors.password} hint={`${PASSWORD_MIN}–${PASSWORD_MAX} ký tự`}>
            {(f) => <PasswordInput {...f} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />}
          </FormField>
        )}
        {canChooseAdmin && (
          <FormField label="Vai trò">
            {(f) => (
              <select {...f} className={selectClass} value={role} onChange={(e) => setRole(e.target.value as Role)}>
                <option value="student">Học sinh</option>
                <option value="admin">Admin</option>
              </select>
            )}
          </FormField>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Huỷ
          </Button>
          <Button type="submit" loading={saving}>
            {user ? 'Lưu' : 'Tạo tài khoản'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
