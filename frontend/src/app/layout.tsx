import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { AppProvider } from '@/store/provider';
import './globals.css';

export const metadata: Metadata = {
  title: { default: 'Examind', template: '%s · Examind' },
  description: 'Nền tảng ôn luyện Toán THPT.',
  icons: {
    icon: { url: '/brand/favicon-48.png', sizes: '48x48', type: 'image/png' },
    apple: { url: '/brand/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex min-h-16 max-w-7xl items-center px-5 sm:px-8">
            <Link href="/" className="inline-flex rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-700">
              <Image
                src="/brand/examind-logo.webp"
                alt="Examind"
                width={972}
                height={285}
                sizes="(min-width: 640px) 168px, 140px"
                className="h-auto w-[140px] sm:w-[168px]"
                preload
              />
            </Link>
          </div>
        </header>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
