'use client';

import { Bell, ChevronDown, Coins, Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Container } from '@/components/layout/container';
import { Logo } from '@/components/layout/logo';
import { IconButton } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { useLogout } from '@/features/auth/use-logout';
import { useTour } from '@/features/onboarding/tour-provider';
import { cn } from '@/lib/cn';
import { mockMode } from '@/lib/config';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppSelector } from '@/store';
import { useStudentAccount } from '../profile/student-account-provider';
import styles from './student-header.module.css';

const navigation = [
  { href: '/dashboard', label: 'Tổng quan' },
  { href: '/exams/new', label: 'Tạo đề với AI' },
  { href: '/exams', label: 'Đề của tôi' },
] as const;

const focusRing = 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring';
const panelStyle = 'absolute top-full z-10 mt-2 rounded-xl bg-background shadow-lift';
const panelLink = cn('flex min-h-11 items-center rounded-lg px-3 text-label font-medium hover:bg-surface-muted', focusRing);

function isUnder(path: string, base: string) {
  return path === base || path.startsWith(`${base}/`);
}

function StudentNavigation({ path, onNavigate }: { path: string; onNavigate?: () => void }) {
  const active = isUnder(path, '/results') ? '/exams' : navigation.find(({ href }) => isUnder(path, href))?.href;

  return (
    <nav aria-label="Điều hướng học tập" className="lg:h-full">
      <ul className="grid gap-1 lg:flex lg:h-full lg:gap-7">
        {navigation.map(({ href, label }) => (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              data-tour={href === '/exams/new' ? 'nav-create' : undefined}
              aria-current={active === href ? 'page' : undefined}
              className={cn(
                'relative flex min-h-11 items-center whitespace-nowrap rounded-lg px-3 text-label transition-colors lg:h-full lg:rounded-none lg:px-0',
                'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
                active === href
                  ? 'bg-primary-subtle text-primary lg:bg-transparent lg:after:absolute lg:after:inset-x-0 lg:after:bottom-0 lg:after:h-0.5 lg:after:bg-primary'
                  : 'text-muted-foreground hover:bg-surface lg:hover:bg-transparent hover:text-foreground',
              )}
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function StudentHeader() {
  const path = usePathname();
  const drawer = useRef<HTMLDialogElement>(null);
  const closeDrawer = () => drawer.current?.close();

  useEffect(() => {
    const dialog = drawer.current;
    const desktop = window.matchMedia('(min-width: 64rem)');
    const onResize = () => {
      if (desktop.matches) dialog?.close();
    };
    desktop.addEventListener('change', onResize);
    return () => desktop.removeEventListener('change', onResize);
  }, []);

  useEffect(() => drawer.current?.close(), [path]);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background">
      <Container className="grid h-[calc(var(--student-header-height)-1px)] grid-cols-[minmax(0,1fr)_auto] items-center gap-2 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:px-10">
        <div className="flex items-center gap-1.5 justify-self-start sm:gap-3">
          <IconButton
            label="Mở điều hướng"
            aria-haspopup="dialog"
            aria-controls="student-navigation"
            data-tour="nav-menu"
            className="-ml-2.5 lg:hidden"
            onClick={() => drawer.current?.showModal()}
          >
            <Menu strokeWidth={1.75} aria-hidden="true" />
          </IconButton>
          <Logo href="/dashboard" className={styles.brand} />
        </div>
        <div className="hidden h-full lg:block">
          <StudentNavigation path={path} />
        </div>
        <HeaderActions key={path} profileActive={isUnder(path, '/profile')} />
      </Container>

      <dialog
        ref={drawer}
        id="student-navigation"
        aria-labelledby="student-navigation-title"
        className={cn(
          'fixed inset-y-0 right-auto left-0 m-0 box-border h-dvh max-h-none w-[min(18rem,calc(100%-2rem))] max-w-none overflow-y-auto overscroll-contain bg-background p-0 text-foreground backdrop:bg-foreground/40',
          styles.drawer,
        )}
        onClick={(event) => {
          if (event.target === event.currentTarget && event.clientX >= event.currentTarget.getBoundingClientRect().right) closeDrawer();
        }}
      >
        <div className="grid gap-4 px-4 pt-[max(0.5rem,env(safe-area-inset-top))] pb-[max(1rem,env(safe-area-inset-bottom))]">
          <div className="flex items-center justify-between gap-2 border-b border-border pb-2">
            <Logo href="/dashboard" className={styles.brand} onClick={closeDrawer} />
            <IconButton autoFocus label="Đóng điều hướng" onClick={closeDrawer}>
              <X strokeWidth={1.75} aria-hidden="true" />
            </IconButton>
          </div>
          <h2 id="student-navigation-title" className="sr-only">Menu học tập</h2>
          <StudentNavigation path={path} onNavigate={closeDrawer} />
        </div>
      </dialog>
    </header>
  );
}

function HeaderActions({ profileActive }: { profileActive: boolean }) {
  const hydrated = useHydrated();
  const user = useAppSelector((state) => state.auth.user);
  const { start: startTour } = useTour();
  const { leaving, logout } = useLogout();
  const router = useRouter();
  const [open, setOpen] = useState<'notifications' | 'account' | null>(null);
  const actions = useRef<HTMLDivElement>(null);
  const bell = useRef<HTMLButtonElement>(null);
  const account = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismissOutside(event: PointerEvent | FocusEvent) {
      if (event.target instanceof Node && !actions.current?.contains(event.target)) setOpen(null);
    }
    document.addEventListener('pointerdown', dismissOutside);
    document.addEventListener('focusin', dismissOutside);
    return () => {
      document.removeEventListener('pointerdown', dismissOutside);
      document.removeEventListener('focusin', dismissOutside);
    };
  }, [open]);

  // `AuthGuard` đảm bảo trang học sinh chỉ mở khi đã đăng nhập, nên tên luôn là của người dùng thật.
  const name = user?.display_name?.trim() || user?.email || '';

  return (
    <div
      ref={actions}
      className="flex items-center gap-1 justify-self-end lg:gap-3"
      onKeyDown={(event) => {
        if (event.key !== 'Escape' || !open) return;
        event.stopPropagation();
        (open === 'notifications' ? bell : account).current?.focus();
        setOpen(null);
      }}
    >
      <CreditPill />
      <div className="sm:relative">
        <IconButton
          ref={bell}
          label="Thông báo"
          className="aria-expanded:bg-surface-muted aria-expanded:text-primary"
          aria-expanded={open === 'notifications'}
          aria-controls="student-notifications"
          onClick={() => setOpen(open === 'notifications' ? null : 'notifications')}
        >
          <Bell strokeWidth={1.75} aria-hidden="true" />
        </IconButton>
        <section
          hidden={open !== 'notifications'}
          id="student-notifications"
          aria-labelledby="student-notifications-title"
          className={cn(panelStyle, 'right-3 w-[min(19rem,calc(100vw-1.5rem))] sm:right-0')}
        >
          <h2 id="student-notifications-title" className="border-b border-border px-4 py-3 text-label font-semibold text-foreground">Thông báo</h2>
          <p className="px-4 py-4 text-caption text-muted-foreground">Bạn chưa có thông báo.</p>
        </section>
      </div>
      <span className="hidden h-6 w-px bg-border lg:block" aria-hidden="true" />

      {!hydrated || !user ? (
        <Skeleton className="size-11 rounded-xl lg:w-40" />
      ) : (
        <div className="sm:relative">
          <button
            ref={account}
            type="button"
            aria-label={`Tài khoản của ${name}`}
            aria-expanded={open === 'account'}
            aria-controls="student-account"
            onClick={() => setOpen(open === 'account' ? null : 'account')}
            className={cn(
              'flex h-11 min-w-11 items-center justify-center gap-2.5 rounded-lg px-1 transition-colors hover:bg-surface aria-expanded:bg-surface-muted lg:justify-start lg:px-2',
              focusRing,
              profileActive && 'text-primary',
            )}
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-subtle text-label font-semibold text-primary" aria-hidden="true">
              {name.charAt(0).toLocaleUpperCase('vi')}
            </span>
            <span className="hidden min-w-0 max-w-28 truncate text-label font-semibold lg:block xl:max-w-40">{name}</span>
            <ChevronDown className="hidden size-3.5 shrink-0 text-muted-foreground lg:block" strokeWidth={1.75} aria-hidden="true" />
          </button>
          <div hidden={open !== 'account'} id="student-account" className={cn(panelStyle, 'right-3 w-[min(17rem,calc(100vw-1.5rem))] sm:right-0')}>
            <div className="border-b border-border px-4 py-3">
              <p className="truncate text-label font-bold text-foreground">{name}</p>
              {user && name !== user.email && <p className="truncate text-caption text-muted-foreground">{user.email}</p>}
              {mockMode && <p className="mt-1 text-caption text-muted-foreground">Điểm luyện tập từ dữ liệu mẫu</p>}
            </div>
            <div className="grid gap-1 p-2">
              <Link href="/profile" aria-current={profileActive ? 'page' : undefined} onClick={() => setOpen(null)} className={cn(panelLink, 'text-foreground')}>
                Hồ sơ
              </Link>
              <button
                type="button"
                className={cn(panelLink, 'text-foreground')}
                onClick={() => {
                  setOpen(null);
                  startTour();
                }}
              >
                Xem lại hướng dẫn
              </button>
              <button
                type="button"
                className={cn(panelLink, 'text-danger disabled:opacity-60')}
                disabled={leaving}
                aria-busy={leaving || undefined}
                onClick={async () => {
                  await logout();
                  setOpen(null);
                  router.replace('/login?reason=logged-out');
                }}
              >
                {leaving ? 'Đang đăng xuất…' : 'Đăng xuất'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Số credit tạo đề còn lại. Bấm để xem chi tiết ở trang hồ sơ. */
function CreditPill() {
  const account = useStudentAccount();
  if (!account) return null;
  if (!account.credits) {
    return account.creditsError ? (
      <button type="button" className={cn('px-2 text-label text-muted-foreground', focusRing)} onClick={account.loadCredits}>
        Tải lại credit
      </button>
    ) : <Skeleton className="h-9 w-16 rounded-full" />;
  }
  const { balance, limit } = account.credits;
  const low = balance < 100;
  return (
    <Link
      href="/profile#credit"
      title={`Còn ${balance}/${limit} credit`}
      aria-label={`Còn ${balance} trên ${limit} credit. Xem chi tiết`}
      className={cn(
        'mr-1 inline-flex h-9 items-center gap-1.5 rounded-full border px-2.5 text-label font-bold tabular-nums transition-colors',
        low ? 'border-border bg-surface-muted text-muted-foreground hover:border-muted-foreground/50' : 'border-ember/50 bg-warning-subtle text-warning hover:border-warning/60',
        focusRing,
      )}
    >
      <Coins className="size-4" strokeWidth={2} aria-hidden="true" />
      {balance}
    </Link>
  );
}
