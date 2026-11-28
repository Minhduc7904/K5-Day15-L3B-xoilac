'use client';

/**
 * Thanh bên khu quản trị: các mục nhóm theo công việc. Dùng chung một phần thân cho hai chỗ:
 * cột cố định trên màn hình lớn (thu gọn được thành cột icon) và ngăn kéo trên màn hình nhỏ.
 */
import { PanelLeftClose, PanelLeftOpen, X } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef } from 'react';
import { Logo } from '@/components/layout/logo';
import { IconButton } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { UserMenu } from '@/features/auth/components/user-menu';
import { ADMIN_NAV_GROUPS, isActiveLink } from './admin-nav';
import { SidebarOnline } from './sidebar-online';

interface SidebarBodyProps {
  path: string;
  /** Chỉ có ý nghĩa ở cột cố định; ngăn kéo luôn hiện đủ chữ. */
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  /** Có trong ngăn kéo: đóng ngăn kéo khi chọn mục hoặc bấm nút đóng. */
  onClose?: () => void;
}

function SidebarBody({ path, collapsed = false, onToggleCollapsed, onClose }: SidebarBodyProps) {
  const inDrawer = onClose !== undefined;
  return (
    <div className="flex h-full flex-col">
      <div className={cn('flex h-14 shrink-0 items-center gap-2 px-4', collapsed && 'justify-center px-0')}>
        <Logo variant={collapsed ? 'mark' : 'full'} href="/admin" priority={!inDrawer} onClick={onClose} />
        {inDrawer && (
          <IconButton label="Đóng menu" size="sm" className="ml-auto" onClick={onClose}>
            <X aria-hidden="true" />
          </IconButton>
        )}
      </div>

      <nav aria-label="Điều hướng quản trị" className={cn('flex-1 px-3 pt-2 pb-4', inDrawer && 'overflow-y-auto')}>
        <div className="grid gap-5">
          {ADMIN_NAV_GROUPS.map((group, index) => (
            <div
              key={group.id}
              role="group"
              aria-labelledby={`nav-${group.id}${inDrawer ? '-d' : ''}`}
              className={cn('grid gap-1', collapsed && index > 0 && 'border-t border-border pt-4')}
            >
              <p
                id={`nav-${group.id}${inDrawer ? '-d' : ''}`}
                className={cn('px-3 pb-1 text-caption font-semibold text-muted-foreground', collapsed && 'sr-only')}
              >
                {group.label}
              </p>
              <ul className="grid gap-1">
                {group.links.map(({ href, label, icon: Icon }) => {
                  const active = isActiveLink(path, href);
                  return (
                    <li key={href}>
                      <Link
                        href={href}
                        onClick={onClose}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'group/nav relative flex h-11 items-center gap-3 rounded-xl px-3 text-label transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                          collapsed && 'justify-center px-0',
                          active
                            ? 'bg-primary-subtle font-semibold text-primary'
                            : 'text-muted-foreground hover:bg-surface-muted hover:text-foreground',
                        )}
                      >
                        <Icon className="size-5 shrink-0" aria-hidden="true" />
                        <span className={cn('min-w-0 truncate', collapsed && 'sr-only')}>{label}</span>
                        {collapsed && (
                          <span
                            aria-hidden="true"
                            className="pointer-events-none absolute top-1/2 left-full z-50 ml-3 -translate-y-1/2 rounded-lg bg-foreground px-2.5 py-1.5 text-caption whitespace-nowrap text-primary-foreground opacity-0 shadow-soft transition-opacity duration-150 group-hover/nav:opacity-100 group-focus-visible/nav:opacity-100"
                          >
                            {label}
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      <div className="grid shrink-0 gap-2 border-t border-border p-3">
        <SidebarOnline collapsed={collapsed} />
        {inDrawer && (
          <div className="flex flex-wrap items-center gap-2 sm:hidden">
            <UserMenu scope="admin" />
          </div>
        )}
        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-pressed={collapsed}
            className={cn(
              'flex h-11 items-center gap-3 rounded-xl px-3 text-label text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring',
              collapsed && 'justify-center px-0',
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-5 shrink-0" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="size-5 shrink-0" aria-hidden="true" />
            )}
            <span className={cn(collapsed && 'sr-only')}>{collapsed ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên'}</span>
          </button>
        )}
      </div>
    </div>
  );
}

/** Cột cố định bên trái cho màn hình lớn. */
export function AdminSidebar({ path, collapsed, onToggleCollapsed }: Omit<SidebarBodyProps, 'onClose'>) {
  return (
    <aside className="sticky top-0 z-40 hidden h-dvh border-r border-border bg-background lg:block">
      <SidebarBody path={path} collapsed={collapsed} onToggleCollapsed={onToggleCollapsed} />
    </aside>
  );
}

/** Ngăn kéo trượt từ trái cho màn hình nhỏ. Dùng <dialog> gốc nên có bẫy focus và Esc để đóng. */
export function AdminDrawer({ open, path, onClose }: { open: boolean; path: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-label="Menu quản trị"
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      className={cn(
        'fixed inset-y-0 left-0 m-0 h-dvh max-h-none w-[min(18rem,85vw)] max-w-none border-r border-border bg-background p-0 text-foreground shadow-lift lg:hidden',
        'backdrop:bg-foreground/40 -translate-x-full transition-transform duration-200 ease-out motion-reduce:transition-none',
        'open:translate-x-0 starting:open:-translate-x-full',
      )}
    >
      {open && <SidebarBody path={path} onClose={onClose} />}
    </dialog>
  );
}
