'use client';

import Image from 'next/image';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { Reveal } from '@/components/motion/reveal';
import { Badge } from '@/components/ui/feedback';
import { mockMode } from '@/lib/config';
import { mockScenarios } from '../mock';

interface AuthHeaderProps {
  icon: ReactNode;
  title: string;
  description: ReactNode;
  /** Ảnh linh vật nhỏ trên mobile, khi panel bên trái bị ẩn. */
  mascot?: string;
}

export function AuthHeader({ icon, title, description, mascot = 'welcome' }: AuthHeaderProps) {
  return (
    <div className="grid gap-4">
      <Image
        src={`/brand/mascot/static/${mascot}.webp`}
        alt=""
        width={384}
        height={384}
        sizes="96px"
        className="mx-auto h-auto w-24 lg:hidden"
        preload
      />
      <span className="hidden size-12 items-center justify-center rounded-2xl bg-primary-subtle text-primary lg:flex [&_svg]:size-6">
        {icon}
      </span>
      <div className="grid gap-2 text-center lg:text-left">
        <h1 className="text-h1 text-foreground">{title}</h1>
        <div className="text-body text-muted-foreground">{description}</div>
      </div>
    </div>
  );
}

export function AuthSwitch({ question, href, label }: { question: string; href: string; label: string }) {
  return (
    <p className="text-center text-body text-muted-foreground">
      {question}{' '}
      <Link
        href={href}
        className="rounded font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {label}
      </Link>
    </p>
  );
}

export function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded text-label font-semibold text-accent-strong underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {children}
    </Link>
  );
}

/** Khung gợi ý tài khoản thử, chỉ hiện khi bật chế độ mock. */
export function MockLoginHint({ onPick }: { onPick: (email: string, password: string) => void }) {
  if (!mockMode) return null;
  return (
    <Reveal y={12} delay={0.2}>
      <div className="grid gap-3 rounded-2xl border-2 border-dashed border-border p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-label font-semibold text-foreground">Tài khoản thử</p>
          <Badge tone="warning">Mock</Badge>
        </div>
        <ul className="grid gap-2 sm:grid-cols-2">
          {mockScenarios.map((s) => (
            <li key={s.email}>
              <button
                type="button"
                onClick={() => onPick(s.email, s.password)}
                className="grid w-full gap-0.5 rounded-xl bg-surface px-3 py-2 text-left transition-colors hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-ring"
              >
                <span className="text-label font-semibold text-foreground">{s.label}</span>
                <span className="text-caption text-muted-foreground">{s.note}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="text-caption text-muted-foreground">Bấm để điền sẵn email và mật khẩu.</p>
      </div>
    </Reveal>
  );
}

export function MockNote({ children }: { children: ReactNode }) {
  if (!mockMode) return null;
  return (
    <div className="flex items-start gap-2 rounded-xl border-2 border-dashed border-border px-3 py-2.5 text-caption text-muted-foreground">
      <Badge tone="warning">Mock</Badge>
      <span className="pt-0.5">{children}</span>
    </div>
  );
}
