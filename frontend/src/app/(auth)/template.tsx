'use client';

import { motion } from 'motion/react';
import type { ReactNode } from 'react';

/** Hiệu ứng vào trang mỗi lần chuyển giữa các trang auth. */
export default function AuthTemplate({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
