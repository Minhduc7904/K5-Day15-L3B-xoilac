'use client';

import { Menu, X } from 'lucide-react';
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from 'motion/react';
import { useEffect, useState, type ReactNode } from 'react';
import { IconButton } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { Container } from './container';
import { Logo } from './logo';

export interface NavLink {
  href: string;
  label: string;
}

interface NavbarProps {
  links?: NavLink[];
  /** Nút bên phải, ví dụ Đăng nhập / Đăng ký. */
  actions?: ReactNode;
  /** id của <main> để link "Bỏ qua tới nội dung". */
  mainId?: string;
}

export function Navbar({ links = [], actions, mainId = 'noi-dung' }: NavbarProps) {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useMotionValueEvent(scrollY, 'change', (y) => setScrolled(y > 12));

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <>
      <a
        href={`#${mainId}`}
        className="sr-only z-[110] rounded-lg bg-primary px-4 py-2 text-label text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Bỏ qua tới nội dung
      </a>
      <header
        className={cn(
          'sticky top-0 z-50 transition-[background-color,box-shadow,border-color] duration-300',
          scrolled || open
            ? 'border-b border-border bg-background/85 shadow-soft backdrop-blur-xl'
            : 'border-b border-transparent bg-transparent',
        )}
      >
        <Container className="flex h-16 items-center gap-6 sm:h-18">
          <Logo priority />

          {links.length > 0 && (
            <nav aria-label="Điều hướng chính" className="hidden flex-1 justify-center md:flex">
              <ul className="flex items-center gap-1">
                {links.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      className="relative rounded-lg px-3 py-2 text-label text-muted-foreground transition-colors after:absolute after:inset-x-3 after:bottom-1 after:h-0.5 after:origin-left after:scale-x-0 after:rounded-full after:bg-accent after:transition-transform after:duration-300 hover:text-foreground hover:after:scale-x-100 focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          )}

          <div className="ml-auto hidden items-center gap-2 md:flex">{actions}</div>

          {(links.length > 0 || actions) && (
            <IconButton
              className="ml-auto md:hidden"
              label={open ? 'Đóng menu' : 'Mở menu'}
              aria-expanded={open}
              aria-controls="menu-di-dong"
              onClick={() => setOpen((v) => !v)}
            >
              {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </IconButton>
          )}
        </Container>

        <AnimatePresence>
          {open && (
            <motion.div
              id="menu-di-dong"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="overflow-hidden md:hidden"
            >
              <Container className="grid gap-1 pt-2 pb-5">
                {links.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="rounded-xl px-3 py-3 text-body font-medium text-foreground hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {link.label}
                  </a>
                ))}
                {actions && <div className="mt-3 grid gap-2 [&>*]:w-full">{actions}</div>}
              </Container>
            </motion.div>
          )}
        </AnimatePresence>
      </header>
    </>
  );
}
