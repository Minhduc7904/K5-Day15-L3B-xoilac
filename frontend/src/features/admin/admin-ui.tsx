'use client';

/** Mảnh giao diện dùng chung cho các trang quản trị (#11): tiêu đề trang, phân trang, hộp xác nhận, ô chọn. */
import type { ReactNode } from 'react';
import { Button, type ButtonVariant } from '@/components/ui/button';
import { fieldBase, fieldState } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { cn } from '@/lib/cn';

export const selectClass = cn(fieldBase, fieldState(false), 'h-11 px-3');

export const formatTime = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString('vi-VN') : '—');

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="grid gap-1">
        <h1 className="text-h3 font-semibold text-foreground">{title}</h1>
        {description && <p className="text-label text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Pagination({ page, pageSize, total, unit, onPage }: {
  page: number; pageSize: number; total: number; unit: string; onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-label">
      <span className="text-muted-foreground">
        {total} {unit} · trang {Math.min(page, pages)}/{pages}
      </span>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Trước
        </Button>
        <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Sau
        </Button>
      </div>
    </div>
  );
}

export function ConfirmModal({ open, title, description, confirmLabel, tone = 'danger', busy, onConfirm, onClose }: {
  open: boolean; title: string; description?: ReactNode; confirmLabel: string; tone?: ButtonVariant; busy?: boolean;
  onConfirm: () => void; onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} description={description}>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          Huỷ
        </Button>
        <Button variant={tone} loading={busy} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border px-4 py-10 text-center text-label text-muted-foreground">
      {children}
    </div>
  );
}
