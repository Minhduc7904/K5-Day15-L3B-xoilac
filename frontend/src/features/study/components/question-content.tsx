'use client';

import { MathContent, type MediaResolver } from '@/components/math/math-content';

/**
 * Hiển thị nội dung câu hỏi. Ảnh `media:ID` được tải qua API theo đề nháp (`draftId`) hoặc theo lượt làm (`attemptId`).
 * Không truyền cả hai thì nội dung không có ảnh (vd. trang minh hoạ của tour).
 */
export function QuestionContent({ source, inline, printable, className, draftId, attemptId }: {
  source: string; inline?: boolean; printable?: boolean; className?: string; draftId?: number; attemptId?: number;
}) {
  const path = attemptId ? `/api/v1/study/attempts/${attemptId}/media/` : draftId ? `/api/v1/exam-chat/drafts/${draftId}/media/` : null;
  const resolver: MediaResolver = (id) => path ? {
    src: path + encodeURIComponent(id),
    alt: 'Hình trong đề', width: 600, height: 400,
  } : undefined;
  return <MathContent source={source} inline={inline} printable={printable} resolveMedia={resolver} className={className} />;
}
