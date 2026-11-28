import type { Metadata, Viewport } from 'next';
import { Be_Vietnam_Pro } from 'next/font/google';
import type { ReactNode } from 'react';
import { AppProvider } from '@/store/provider';
import './globals.css';

// Họ font duy nhất của dự án. Không nhúng font ở nơi khác.
const beVietnamPro = Be_Vietnam_Pro({
  subsets: ['latin', 'vietnamese'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-be-vietnam-pro',
});

export const metadata: Metadata = {
  title: { default: 'Examind — Ôn Toán đúng chương mình còn yếu', template: '%s · Examind' },
  description:
    'Examind đề xuất cấu trúc đề ôn Toán THPT theo chương bạn hay sai, để bạn duyệt rồi ghép đề nháp từ câu hỏi đã được duyệt.',
  icons: {
    icon: { url: '/brand/favicon-48.png', sizes: '48x48', type: 'image/png' },
    apple: { url: '/brand/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
  },
};

// Đồng bộ tay với token --color-foreground trong globals.css.
export const viewport: Viewport = { themeColor: '#03172f' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" className={beVietnamPro.variable} data-scroll-behavior="smooth">
      <head>
        <noscript>
          <style>{'[data-splash]{display:none!important}html{overflow:auto!important}'}</style>
        </noscript>
      </head>
      <body className="min-h-dvh font-sans">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
