'use client';

import Image from 'next/image';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { Reveal } from '@/components/motion/reveal';
import { Badge } from '@/components/ui/feedback';

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
