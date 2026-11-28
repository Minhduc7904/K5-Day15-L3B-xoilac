'use client';

/**
 * Màn quản lý người dùng cho admin (#20): tìm, lọc, phân trang, tạo, sửa, khoá/mở khoá, đặt lại mật khẩu.
 * Thao tác mà backend sẽ trả 403 thì ẩn (canManage); backend vẫn là nơi quyết định.
 */
import { KeyRound, Lock, LockOpen, Pencil, Plus, Search } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { useToast } from '@/components/ui/toast';
import { toApiError, type ApiError } from '@/lib/api-error';
import { adminUsersApi } from '../api';
import { canManage, type Principal } from '../permissions';
import type { AdminUser, Role, Status, UserList } from '../types';
import { ResetPasswordModal } from './reset-password-modal';
import { selectClass, UserFormModal } from './user-form-modal';

const PAGE_SIZE = 10;

function useDebounced<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

const formatTime = (iso: string | null) => (iso ? new Date(iso).toLocaleString('vi-VN') : '—');

export function UserManagement({ actor }: { actor: Principal }) {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [role, setRole] = useState<Role | ''>('');
  const [status, setStatus] = useState<Status | ''>('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<UserList | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [editing, setEditing] = useState<AdminUser | null | undefined>(undefined); // undefined: đóng, null: tạo mới
  const [resetting, setResetting] = useState<AdminUser | null>(null);
  const [locking, setLocking] = useState<AdminUser | null>(null);
  const [busy, setBusy] = useState(false);
  const search = useDebounced(q);

  const load = useCallback(async () => {
    try {
      setData(await adminUsersApi.list({ q: search, role: role || undefined, status: status || undefined, page, page_size: PAGE_SIZE }));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [search, role, status, page]);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => setPage(1), [search, role, status]);

  const can = (target: AdminUser, action: 'update' | 'reset_password', changes = {}) =>
    canManage(actor, target, action, changes) === null;

  const toggleStatus = async (user: AdminUser) => {
    const next: Status = user.status === 'active' ? 'disabled' : 'active';
    setBusy(true);
    try {
      await adminUsersApi.update(user.user_id, { status: next });
      toast({
        tone: 'success',
        title: next === 'disabled' ? 'Đã khoá tài khoản' : 'Đã mở khoá tài khoản',
        description: next === 'disabled' ? `${user.email} bị đăng xuất khỏi mọi thiết bị.` : `${user.email} đăng nhập lại được.`,
      });
      setLocking(null);
      await load();
    } catch (e) {
      toast({ tone: 'danger', title: 'Không đổi được trạng thái', description: toApiError(e).message });
    } finally {
      setBusy(false);
    }
  };

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <CardTitle>Quản lý người dùng</CardTitle>
        <Button size="sm" leftIcon={<Plus aria-hidden="true" />} onClick={() => setEditing(null)}>
          Tạo tài khoản
        </Button>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <Input
            aria-label="Tìm theo email hoặc tên"
            placeholder="Tìm theo email hoặc tên"
            leftIcon={<Search aria-hidden="true" />}
            value={q}
            maxLength={100}
            onChange={(e) => setQ(e.target.value)}
          />
          <select aria-label="Lọc vai trò" className={selectClass} value={role} onChange={(e) => setRole(e.target.value as Role | '')}>
            <option value="">Mọi vai trò</option>
            <option value="student">Học sinh</option>
            <option value="admin">Admin</option>
          </select>
          <select aria-label="Lọc trạng thái" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value as Status | '')}>
            <option value="">Mọi trạng thái</option>
            <option value="active">Đang hoạt động</option>
            <option value="disabled">Đã khoá</option>
          </select>
        </div>

        {error && <Alert tone="danger" title="Không tải được danh sách">{error.message}</Alert>}
        {!data && !error && <Skeleton className="h-48 w-full" />}

        {data && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-left text-label">
              <thead className="text-caption text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 font-medium">Tài khoản</th>
                  <th className="py-2 pr-3 font-medium">Vai trò</th>
                  <th className="py-2 pr-3 font-medium">Trạng thái</th>
                  <th className="py-2 pr-3 font-medium">Đăng nhập gần nhất</th>
                  <th className="py-2 font-medium text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-muted-foreground">
                      Không có tài khoản nào khớp bộ lọc.
                    </td>
                  </tr>
                )}
                {data.items.map((u) => {
                  const lockChange = { status: u.status === 'active' ? ('disabled' as const) : ('active' as const) };
                  return (
                    <tr key={u.user_id} className="border-b border-border/60">
                      <td className="py-2.5 pr-3">
                        <p className="font-medium text-foreground">{u.display_name ?? '—'}</p>
                        <p className="text-caption text-muted-foreground">{u.email}</p>
                      </td>
                      <td className="py-2.5 pr-3">
                        <div className="flex flex-wrap gap-1">
                          <Badge tone={u.role === 'admin' ? 'primary' : 'neutral'}>{u.role === 'admin' ? 'Admin' : 'Học sinh'}</Badge>
                          {u.is_root && <Badge tone="accent">Admin gốc</Badge>}
                          {u.user_id === actor.user_id && <Badge tone="info">Bạn</Badge>}
                        </div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge tone={u.status === 'active' ? 'success' : 'danger'} dot>
                          {u.status === 'active' ? 'Hoạt động' : 'Đã khoá'}
                        </Badge>
                      </td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{formatTime(u.last_login_at)}</td>
                      <td className="py-2.5">
                        <div className="flex justify-end gap-1">
                          {can(u, 'update', { display_name: u.display_name }) && (
                            <Button size="sm" variant="ghost" leftIcon={<Pencil aria-hidden="true" />} onClick={() => setEditing(u)}>
                              Sửa
                            </Button>
                          )}
                          {can(u, 'update', lockChange) && (
                            <Button
                              size="sm"
                              variant="ghost"
                              leftIcon={u.status === 'active' ? <Lock aria-hidden="true" /> : <LockOpen aria-hidden="true" />}
                              onClick={() => (u.status === 'active' ? setLocking(u) : void toggleStatus(u))}
                              disabled={busy}
                            >
                              {u.status === 'active' ? 'Khoá' : 'Mở khoá'}
                            </Button>
                          )}
                          {can(u, 'reset_password') && (
                            <Button size="sm" variant="ghost" leftIcon={<KeyRound aria-hidden="true" />} onClick={() => setResetting(u)}>
                              Đặt lại mật khẩu
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-label">
            <span className="text-muted-foreground">
              {data.total} tài khoản · trang {page}/{pages}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Trước
              </Button>
              <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                Sau
              </Button>
            </div>
          </div>
        )}
      </CardContent>

      <UserFormModal
        open={editing !== undefined}
        actor={actor}
        user={editing ?? null}
        onClose={() => setEditing(undefined)}
        onSaved={(u) => {
          setEditing(undefined);
          toast({ tone: 'success', title: editing ? 'Đã lưu' : 'Đã tạo tài khoản', description: u.email });
          void load();
        }}
      />
      <ResetPasswordModal
        user={resetting}
        onClose={() => setResetting(null)}
        onDone={(u) => {
          setResetting(null);
          toast({ tone: 'success', title: 'Đã đặt lại mật khẩu', description: `${u.email} bị đăng xuất khỏi mọi thiết bị.` });
        }}
      />
      <Modal
        open={locking !== null}
        onClose={() => setLocking(null)}
        title="Khoá tài khoản?"
        description={locking ? `${locking.email} sẽ bị đăng xuất khỏi mọi thiết bị và không đăng nhập được cho tới khi mở khoá.` : undefined}
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setLocking(null)}>
            Huỷ
          </Button>
          <Button variant="danger" loading={busy} onClick={() => locking && void toggleStatus(locking)}>
            Khoá
          </Button>
        </div>
      </Modal>
    </Card>
  );
}
