'use client';

import { Bell, CheckCheck } from 'lucide-react';
import Link from 'next/link';
import type { Ref } from 'react';
import { IconButton } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import type { Notification } from './api';
import type { useNotifications } from './use-notifications';

type Notifications = ReturnType<typeof useNotifications>;

/** "vừa xong", "5 phút trước", "2 giờ trước", "Hôm qua", rồi tới ngày cụ thể. */
function timeAgo(iso: string) {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60_000));
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)} giờ trước`;
  if (minutes < 60 * 48) return 'Hôm qua';
  return new Date(iso).toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' });
}

const itemStyle = 'grid min-h-11 gap-0.5 rounded-lg px-3 py-2.5 text-left hover:bg-surface-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring';

function Item({ item, onOpen }: { item: Notification; onOpen: (item: Notification) => void }) {
  const unread = item.read_at === null;
  const content = (
    <>
      <span className="flex items-start gap-2">
        {unread && <i className="mt-1.5 size-2 shrink-0 rounded-full bg-flame-strong" aria-hidden="true" />}
        <span className={cn('min-w-0 text-label text-foreground', unread ? 'font-semibold' : 'font-medium')}>
          {item.title}
          {unread && <span className="sr-only"> (chưa đọc)</span>}
        </span>
      </span>
      {item.body && <span className={cn('text-caption text-muted-foreground', unread && 'pl-4')}>{item.body}</span>}
      <span className={cn('text-caption text-muted-foreground/80', unread && 'pl-4')}>{timeAgo(item.created_at)}</span>
    </>
  );
  return item.link ? (
    <Link href={item.link} onClick={() => onOpen(item)} className={itemStyle}>{content}</Link>
  ) : (
    <button type="button" onClick={() => onOpen(item)} className={cn(itemStyle, 'w-full')}>{content}</button>
  );
}

/** Nút chuông kèm số chưa đọc. Phần bảng danh sách do `NotificationList` vẽ. */
export function NotificationBell({ unread, expanded, onClick, buttonRef }: {
  unread: number; expanded: boolean; onClick: () => void; buttonRef: Ref<HTMLButtonElement>;
}) {
  return (
    <div className="relative">
      <IconButton
        ref={buttonRef}
        label={unread > 0 ? `Thông báo, ${unread} chưa đọc` : 'Thông báo'}
        className="aria-expanded:bg-surface-muted aria-expanded:text-primary"
        aria-expanded={expanded}
        aria-controls="student-notifications"
        onClick={onClick}
      >
        <Bell strokeWidth={1.75} aria-hidden="true" />
      </IconButton>
      {unread > 0 && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-1 right-1 grid min-w-4 place-items-center rounded-full bg-flame-strong px-1 text-[0.625rem] leading-4 font-bold text-primary-foreground tabular-nums"
        >
          {unread > 9 ? '9+' : unread}
        </span>
      )}
    </div>
  );
}

export function NotificationList({ data, onNavigate }: { data: Notifications; onNavigate: () => void }) {
  const { items, unread, status, reload, markRead, markAll } = data;
  return (
    <>
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <h2 id="student-notifications-title" className="text-label font-semibold text-foreground">Thông báo</h2>
        {unread > 0 && (
          <button
            type="button"
            onClick={() => void markAll()}
            className="inline-flex items-center gap-1 rounded-md text-caption font-semibold text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <CheckCheck className="size-3.5" aria-hidden="true" /> Đã đọc hết
          </button>
        )}
      </div>
      {status === 'loading' && <p className="px-4 py-4 text-caption text-muted-foreground" aria-busy="true">Đang tải…</p>}
      {status === 'error' && (
        <div className="grid justify-items-start gap-2 px-4 py-4">
          <p className="text-caption text-muted-foreground">Chưa tải được thông báo.</p>
          <button type="button" onClick={() => void reload()} className="rounded-md text-caption font-semibold text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            Thử lại
          </button>
        </div>
      )}
      {status === 'ready' && items.length === 0 && <p className="px-4 py-4 text-caption text-muted-foreground">Bạn chưa có thông báo.</p>}
      {items.length > 0 && (
        <ul className="max-h-[min(24rem,70dvh)] overflow-y-auto overscroll-contain p-1.5">
          {items.map((item) => (
            <li key={item.id}>
              <Item item={item} onOpen={(opened) => { void markRead(opened.id); onNavigate(); }} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
