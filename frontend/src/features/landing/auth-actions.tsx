'use client';

import { ArrowRight, LogIn, LogOut } from 'lucide-react';
import { useState } from 'react';
import { Button, type ButtonSize, type ButtonVariant } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { authApi } from '@/features/auth/api';
import { signedOut } from '@/features/auth/auth-slice';
import { useHydrated } from '@/lib/use-hydrated';
import { useAppDispatch, useAppSelector } from '@/store';

const hrefs = { login: '/login', register: '/register' } as const;

export function NavAuthActions() {
  const { user, status } = useAppSelector((s) => s.auth);
  const dispatch = useAppDispatch();
  const toast = useToast();
  const [leaving, setLeaving] = useState(false);
  const hydrated = useHydrated();

  if (!hydrated || status === 'unknown') return <Skeleton className="h-9 w-48 rounded-xl" />;

  if (user) {
    const name = user.display_name ?? user.email;
    const logout = async () => {
      setLeaving(true);
      try {
        await authApi.logout();
        dispatch(signedOut());
        toast({ tone: 'info', title: 'Đã đăng xuất', description: 'Hẹn gặp lại bạn ở buổi ôn tiếp theo.' });
      } finally {
        setLeaving(false);
      }
    };
    return (
      <>
        <span className="flex items-center gap-2 rounded-xl bg-surface px-3 py-1.5 text-label text-foreground">
          <span
            className="flex size-7 items-center justify-center rounded-full bg-primary text-caption font-bold text-primary-foreground"
            aria-hidden="true"
          >
            {name.charAt(0).toUpperCase()}
          </span>
          <span className="max-w-40 truncate">{name}</span>
        </span>
        <Button variant="ghost" size="sm" leftIcon={<LogOut aria-hidden="true" />} onClick={logout} loading={leaving}>
          Đăng xuất
        </Button>
      </>
    );
  }

  return (
    <>
      <Button href={hrefs.login} variant="ghost" size="sm" leftIcon={<LogIn aria-hidden="true" />}>
        Đăng nhập
      </Button>
      <Button href={hrefs.register} size="sm">
        Tạo tài khoản
      </Button>
    </>
  );
}

interface AuthButtonProps {
  kind: keyof typeof hrefs;
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: string;
  arrow?: boolean;
}

export function AuthButton({ kind, variant = 'primary', size = 'lg', children, arrow }: AuthButtonProps) {
  return (
    <Button
      href={hrefs[kind]}
      variant={variant}
      size={size}
      leftIcon={kind === 'login' && !arrow ? <LogIn aria-hidden="true" /> : undefined}
      rightIcon={
        arrow ? (
          <ArrowRight aria-hidden="true" className="transition-transform duration-200 group-hover/button:translate-x-1" />
        ) : undefined
      }
    >
      {children}
    </Button>
  );
}
