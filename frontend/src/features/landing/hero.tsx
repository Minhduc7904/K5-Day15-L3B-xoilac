'use client';

import { Check, Sparkles } from 'lucide-react';
import Image from 'next/image';
import { motion } from 'motion/react';
import { Container } from '@/components/layout/container';
import { Float, Stagger, StaggerItem } from '@/components/motion/reveal';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/feedback';
import { ChatDemo } from './chat-demo';

const promises = ['Nêu rõ căn cứ bằng số liệu', 'Bạn duyệt trước khi tạo đề', 'Chỉ dùng câu đã được duyệt'];

const mathChips = [
  { text: "f'(x) = 0", className: '-left-10 top-24', delay: 0 },
  { text: '∫₀¹ x² dx', className: '-right-6 top-[46%]', delay: 1.2 },
  { text: 'log₂ 8 = 3', className: '-left-6 bottom-20', delay: 0.6 },
];

function Highlight({ children }: { children: string }) {
  return (
    <span className="relative inline-block whitespace-nowrap text-primary">
      {children}
      <svg
        viewBox="0 0 300 16"
        preserveAspectRatio="none"
        className="absolute -bottom-1.5 left-0 h-3 w-full text-accent"
        aria-hidden="true"
      >
        <motion.path
          d="M3 11 C 60 3, 140 3, 297 9"
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.9, duration: 0.8, ease: 'easeInOut' }}
        />
      </svg>
    </span>
  );
}

function Sparkle({ className }: { className: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path d="M12 0c.6 6.2 5.8 11.4 12 12-6.2.6-11.4 5.8-12 12-.6-6.2-5.8-11.4-12-12C6.2 11.4 11.4 6.2 12 0Z" fill="currentColor" />
    </svg>
  );
}

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden pt-8 pb-20 sm:pt-14 sm:pb-28">
      <div className="bg-grid mask-fade pointer-events-none absolute inset-0" aria-hidden="true" />
      <div
        className="pointer-events-none absolute -top-48 -right-32 size-[620px] rounded-full bg-accent/15 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-40 -left-40 size-[520px] rounded-full bg-primary/10 blur-3xl"
        aria-hidden="true"
      />

      <Container className="relative grid items-center gap-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12">
        <Stagger immediate className="grid justify-items-start gap-6">
          <StaggerItem>
            <Badge tone="accent" icon={<Sparkles aria-hidden="true" />}>
              Dành cho học sinh lớp 10–12
            </Badge>
          </StaggerItem>
          <StaggerItem>
            <h1 id="hero-title" className="text-display text-balance text-foreground">
              Ôn đúng phần{' '}
              <span className="whitespace-nowrap">
                <Highlight>mình còn yếu</Highlight>,
              </span>{' '}
              không ôn lan man.
            </h1>
          </StaggerItem>
          <StaggerItem>
            <p className="max-w-xl text-body-lg text-pretty text-muted-foreground">
              Nhắn cho Examind bạn muốn ôn gì. Examind xem lịch sử làm bài, đề xuất cấu trúc đề theo chương, số câu và
              độ khó để bạn duyệt, rồi ghép đề nháp từ các câu hỏi đã được duyệt.
            </p>
          </StaggerItem>
          <StaggerItem className="flex flex-wrap gap-3">
            <Button variant="outline" size="lg" href="#cach-hoat-dong">
              Xem cách hoạt động
            </Button>
          </StaggerItem>
          <StaggerItem>
            <ul className="flex flex-wrap gap-x-5 gap-y-2">
              {promises.map((item) => (
                <li key={item} className="flex items-center gap-2 text-label text-muted-foreground">
                  <span className="flex size-5 items-center justify-center rounded-full bg-success-subtle text-success">
                    <Check className="size-3" strokeWidth={3} aria-hidden="true" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </StaggerItem>
        </Stagger>

        <motion.div
          initial={{ opacity: 0, y: 40, rotate: 1.5 }}
          animate={{ opacity: 1, y: 0, rotate: 0 }}
          transition={{ delay: 0.3, duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="relative mx-auto w-full max-w-md pt-14 lg:max-w-none lg:pt-10"
        >
          <Float className="absolute -top-4 right-0 z-10 w-28 sm:-right-4 sm:w-36" distance={12} duration={4.5}>
            <Image
              src="/brand/mascot/static/welcome.webp"
              alt="Linh vật Examind vẫy tay chào"
              width={384}
              height={384}
              sizes="144px"
              className="h-auto w-full drop-shadow-mascot"
              preload
            />
          </Float>

          <Sparkle className="animate-twinkle absolute top-6 left-6 size-6 text-accent" />
          <Sparkle className="animate-twinkle absolute -bottom-2 right-16 size-4 text-primary/50 [animation-delay:1.1s]" />

          {mathChips.map((chip) => (
            <Float
              key={chip.text}
              delay={chip.delay}
              distance={8}
              duration={6}
              className={`absolute z-10 hidden xl:block ${chip.className}`}
            >
              <span
                className="block rounded-xl border border-border bg-background/90 px-3 py-1.5 text-label font-semibold text-primary shadow-soft backdrop-blur"
                aria-hidden="true"
              >
                {chip.text}
              </span>
            </Float>
          ))}

          <ChatDemo />
        </motion.div>
      </Container>
    </section>
  );
}
