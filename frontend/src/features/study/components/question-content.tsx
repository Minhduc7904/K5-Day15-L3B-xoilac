'use client';

import { MathContent, type MediaResolver } from '@/components/math/math-content';
import { mockMedia } from '../fixtures/questions';

/** Tra ảnh `media:ID`. Mock dùng ảnh tự vẽ; bản thật sẽ lấy URL MinIO từ API. */
export const resolveMedia: MediaResolver = (id) => mockMedia[id];

export function QuestionContent({ source, inline, printable, className, draftId }: { source: string; inline?: boolean; printable?: boolean; className?: string; draftId?: number }) {
  const resolver: MediaResolver = draftId ? (id) => ({
    src: '/api/v1/exam-chat/drafts/' + draftId + '/media/' + encodeURIComponent(id),
    alt: 'Hình trong đề', width: 600, height: 400,
  }) : resolveMedia;
  return <MathContent source={source} inline={inline} printable={printable} resolveMedia={resolver} className={className} />;
}
