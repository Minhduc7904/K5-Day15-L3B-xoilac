'use client';

import { MathContent, type MediaResolver } from '@/components/math/math-content';
import { mockMedia } from '../fixtures/questions';

/** Tra ảnh `media:ID`. Mock dùng ảnh tự vẽ; bản thật sẽ lấy URL MinIO từ API. */
export const resolveMedia: MediaResolver = (id) => mockMedia[id];

export function QuestionContent({ source, inline, printable, className }: { source: string; inline?: boolean; printable?: boolean; className?: string }) {
  return <MathContent source={source} inline={inline} printable={printable} resolveMedia={resolveMedia} className={className} />;
}
