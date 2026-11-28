'use client';

/**
 * Hiển thị một câu như học sinh thấy (công thức KaTeX, ảnh `media:ID`), kèm đáp án và lời giải cho admin.
 * Dùng chung cho trang chi tiết và ô xem trước của form.
 */
import { Check, X } from 'lucide-react';
import { MathContent, type MediaResolver } from '@/components/math/math-content';
import { Badge } from '@/components/ui/feedback';
import { cn } from '@/lib/cn';
import { questionMediaUrl } from '../api';
import type { QuestionType } from '../types';

const resolver: MediaResolver = (id) => ({ src: questionMediaUrl(id), alt: 'Hình trong câu hỏi', width: 600, height: 400 });

export function AdminQuestionContent({ source, inline, className }: { source: string; inline?: boolean; className?: string }) {
  return <MathContent source={source} inline={inline} resolveMedia={resolver} className={className} />;
}

export const optionLabel = (type: QuestionType, index: number) =>
  type === 'TRUE_FALSE' ? `${String.fromCharCode(97 + index)})` : `${String.fromCharCode(65 + index)}.`;

export function QuestionView({ type, content, statements, correctAnswer, solution }: {
  type: QuestionType;
  content: string;
  statements: Array<{ content: string; is_correct: boolean }>;
  correctAnswer?: string | null;
  solution?: string | null;
}) {
  return (
    <div className="grid gap-4">
      {content.trim() ? <AdminQuestionContent source={content} /> : <p className="text-muted-foreground">Chưa có nội dung.</p>}
      {statements.length > 0 && (
        <ul className="grid gap-2">
          {statements.map((s, i) => (
            <li
              key={i}
              className={cn(
                'flex items-start gap-2 rounded-xl border px-3 py-2',
                s.is_correct ? 'border-success/40 bg-success-subtle' : 'border-border',
              )}
            >
              <b className="shrink-0">{optionLabel(type, i)}</b>
              <AdminQuestionContent source={s.content} inline className="min-w-0 flex-1" />
              {type === 'TRUE_FALSE' ? (
                <Badge tone={s.is_correct ? 'success' : 'danger'}>{s.is_correct ? 'Đúng' : 'Sai'}</Badge>
              ) : s.is_correct ? (
                <Check className="size-4 shrink-0 text-success" aria-label="Đáp án đúng" />
              ) : (
                <X className="size-4 shrink-0 text-muted-foreground/50" aria-hidden="true" />
              )}
            </li>
          ))}
        </ul>
      )}
      {correctAnswer && (
        <p className="text-label">
          <span className="text-muted-foreground">Đáp án: </span>
          <b>{correctAnswer}</b>
        </p>
      )}
      {solution && (
        <div className="grid gap-1.5 rounded-xl bg-surface-muted p-3">
          <p className="text-caption font-semibold text-muted-foreground uppercase">Lời giải</p>
          <AdminQuestionContent source={solution} className="text-body" />
        </div>
      )}
    </div>
  );
}
