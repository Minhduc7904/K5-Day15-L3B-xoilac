'use client';

import { motion } from 'motion/react';
import Image from 'next/image';
import { cn } from '@/lib/cn';

/** `run` là vòng lặp chạy; còn lại là ảnh tĩnh trong `public/brand/mascot/static`. */
export type MascotLook = 'welcome' | 'working' | 'studying' | 'success' | 'front' | 'left' | 'right' | 'run';

export const MASCOT_SOURCES: Record<MascotLook, string> = {
  welcome: '/brand/mascot/static/welcome.webp',
  working: '/brand/mascot/static/working.webp',
  studying: '/brand/mascot/static/studying.webp',
  success: '/brand/mascot/static/success.webp',
  front: '/brand/mascot/static/front.webp',
  left: '/brand/mascot/static/left.webp',
  right: '/brand/mascot/static/right.webp',
  run: '/brand/mascot/running/loop.webp',
};

interface TourMascotProps {
  look: MascotLook;
  size: number;
  /** Lật ngang, dùng khi chạy sang trái (ảnh chạy nghiêng sang phải). */
  flip?: boolean;
  /** Nhún nhẹ khi đứng yên. */
  bob?: boolean;
}

export function TourMascot({ look, size, flip = false, bob = false }: TourMascotProps) {
  return (
    <motion.div
      aria-hidden="true"
      animate={bob ? { y: [0, -4, 0] } : { y: 0 }}
      transition={bob ? { duration: 3.2, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.2 }}
      className="relative shrink-0"
      style={{ width: size }}
    >
      <Image
        src={MASCOT_SOURCES[look]}
        alt=""
        width={384}
        height={384}
        unoptimized
        priority
        className={cn('pixelated h-auto w-full drop-shadow-mascot', flip && '-scale-x-100')}
      />
    </motion.div>
  );
}
