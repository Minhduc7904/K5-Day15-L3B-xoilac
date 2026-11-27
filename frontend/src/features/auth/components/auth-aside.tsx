'use client';

import { Check } from 'lucide-react';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { AnimatePresence, motion } from 'motion/react';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { Float } from '@/components/motion/reveal';

type Art = { kind: 'static'; file: string } | { kind: 'motion'; motion: 'thinking' | 'running' };

const content: Record<string, { art: Art; title: string; body: string }> = {
  '/login': {
    art: { kind: 'static', file: 'welcome' },
    title: 'Chào bạn quay lại!',
    body: 'Tiếp tục ôn đúng những chương bạn còn yếu.',
  },
  '/register': {
    art: { kind: 'static', file: 'success' },
    title: 'Bắt đầu ôn có định hướng',
    body: 'Tạo tài khoản học sinh miễn phí trong một phút.',
  },
  '/forgot-password': {
    art: { kind: 'motion', motion: 'thinking' },
    title: 'Quên mật khẩu? Không sao',
    body: 'Mình gửi mã xác minh tới email để bạn đặt lại.',
  },
  '/verify-otp': {
    art: { kind: 'static', file: 'working' },
    title: 'Kiểm tra hộp thư nhé',
    body: 'Mã gồm 6 chữ số, có hiệu lực trong 5 phút.',
  },
  '/reset-password': {
    art: { kind: 'static', file: 'studying' },
    title: 'Sắp xong rồi',
    body: 'Đặt mật khẩu mới để quay lại với việc ôn tập.',
  },
};

const points = ['Đề ôn theo chương bạn hay sai', 'Xem trước và chỉnh cấu trúc đề', 'Chỉ dùng câu hỏi đã được duyệt'];
const chips = [
  { text: 'sin²x + cos²x = 1', className: 'top-[14%] right-[12%]', delay: 0 },
  { text: 'Cₙᵏ', className: 'top-[46%] left-[8%]', delay: 0.8 },
  { text: 'y′ = 3x² − 3', className: 'bottom-[20%] right-[10%]', delay: 1.6 },
];

export function AuthAside() {
  const pathname = usePathname();
  const page = content[pathname] ?? content['/login'];

  return (
    <aside className="relative hidden overflow-hidden bg-linear-to-br from-primary to-foreground text-primary-foreground lg:flex lg:flex-col">
      <div className="bg-grid-inverse pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="pointer-events-none absolute -top-32 -left-24 size-96 rounded-full bg-accent/25 blur-3xl" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-24 -bottom-24 size-96 rounded-full bg-accent/15 blur-3xl" aria-hidden="true" />

      {chips.map((chip) => (
        <Float key={chip.text} delay={chip.delay} distance={8} duration={6} className={`absolute ${chip.className}`}>
          <span
            className="block rounded-xl border border-primary-foreground/15 bg-primary-foreground/10 px-3 py-1.5 text-label font-semibold backdrop-blur"
            aria-hidden="true"
          >
            {chip.text}
          </span>
        </Float>
      ))}

      <div className="relative flex flex-1 flex-col justify-between p-10 xl:p-14">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-2xl bg-background p-1.5 shadow-soft">
            <Image src="/brand/examind-mark.png" alt="" width={64} height={64} className="size-full" />
          </span>
          <span className="text-h3 font-bold">Examind</span>
        </div>

        <div className="grid justify-items-start gap-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 24, scale: 0.92 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -16, scale: 0.95 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="grid gap-6"
            >
              <Float distance={10} duration={4.5} className="w-44 xl:w-52">
                {page.art.kind === 'static' ? (
                  <Image
                    src={`/brand/mascot/static/${page.art.file}.webp`}
                    alt=""
                    width={384}
                    height={384}
                    sizes="208px"
                    className="drop-shadow-mascot h-auto w-full"
                    preload
                  />
                ) : (
                  <MascotAnimation motion={page.art.motion} size={208} />
                )}
              </Float>
              <div className="grid max-w-md gap-3">
                <p className="text-h1 text-balance">{page.title}</p>
                <p className="text-body-lg text-primary-foreground/80">{page.body}</p>
              </div>
            </motion.div>
          </AnimatePresence>

          <ul className="grid gap-3">
            {points.map((point) => (
              <li key={point} className="flex items-center gap-3 text-body text-primary-foreground/90">
                <span className="flex size-6 items-center justify-center rounded-full bg-accent text-foreground">
                  <Check className="size-3.5" strokeWidth={3} aria-hidden="true" />
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-caption text-primary-foreground/70">
          Đề do Examind tạo là đề luyện tập, không phải đề hay điểm chính thức.
        </p>
      </div>
    </aside>
  );
}
