'use client';

import { motion, type Variants } from 'motion/react';
import type { ReactNode } from 'react';

const ease = [0.22, 1, 0.36, 1] as const;

interface RevealProps {
  children: ReactNode;
  delay?: number;
  /** Quãng trượt lên khi xuất hiện, tính bằng px. */
  y?: number;
  className?: string;
}

/** Hiện dần khi cuộn tới. Tự tắt khi người dùng bật giảm chuyển động (MotionConfig ở AppProvider). */
export function Reveal({ children, delay = 0, y = 28, className }: RevealProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, ease, delay }}
    >
      {children}
    </motion.div>
  );
}

const container: Variants = {
  hidden: {},
  show: (stagger: number) => ({ transition: { staggerChildren: stagger } }),
};

const item: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease } },
};

interface StaggerProps {
  children: ReactNode;
  className?: string;
  stagger?: number;
  /** Chạy ngay khi tải thay vì chờ cuộn tới, dùng cho hero. */
  immediate?: boolean;
}

export function Stagger({ children, className, stagger = 0.09, immediate }: StaggerProps) {
  return (
    <motion.div
      className={className}
      variants={container}
      custom={stagger}
      initial="hidden"
      {...(immediate ? { animate: 'show' } : { whileInView: 'show', viewport: { once: true, margin: '-60px' } })}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}

interface FloatProps {
  children: ReactNode;
  className?: string;
  /** Biên độ lơ lửng, px. */
  distance?: number;
  duration?: number;
  delay?: number;
}

export function Float({ children, className, distance = 10, duration = 5, delay = 0 }: FloatProps) {
  return (
    <motion.div
      className={className}
      animate={{ y: [0, -distance, 0] }}
      transition={{ duration, delay, repeat: Infinity, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  );
}
