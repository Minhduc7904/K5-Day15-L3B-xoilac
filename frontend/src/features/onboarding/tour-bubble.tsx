'use client';

import { ArrowRight, ChevronLeft } from 'lucide-react';
import { Button, IconButton } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import type { TourChapterId } from './steps';
import { TourProgress } from './tour-progress';

interface TourBubbleProps {
  titleId: string;
  bodyId: string;
  title: string;
  body: string;
  chapter: TourChapterId;
  chapters: ReadonlyArray<{ id: string; label: string }>;
  first: boolean;
  last: boolean;
  /** Điện thoại: bong bóng dưới linh vật, rộng hết thẻ. */
  sheet: boolean;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onFinish: (href?: string) => void;
}

/** Bong bóng nói của linh vật: nội dung bước, tiến độ và các nút điều khiển. */
export function TourBubble({ titleId, bodyId, title, body, chapter, chapters, first, last, sheet, onNext, onPrev, onSkip, onFinish }: TourBubbleProps) {
  const intro = chapter === 'intro';
  const outro = last;

  return (
    <div className={cn('relative min-w-0 bg-background p-4 text-foreground shadow-lift sm:p-5', sheet ? 'w-full rounded-2xl' : 'flex-1 rounded-2xl rounded-bl-sm')}>
      {!sheet && (
        <svg aria-hidden="true" viewBox="0 0 14 14" className="absolute -left-[11px] bottom-0 size-3.5 fill-background">
          <path d="M14 0v14H0C7 12 12 7 14 0z" />
        </svg>
      )}

      <div className="flex items-start justify-between gap-3">
        <h2 id={titleId} className="text-h3 text-balance">{title}</h2>
        {!intro && !outro && (
          <button
            type="button"
            onClick={onSkip}
            className="-mt-2.5 -mr-2 inline-flex min-h-11 shrink-0 items-center rounded-lg px-2 text-caption font-semibold text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            Bỏ qua hướng dẫn
          </button>
        )}
      </div>
      <p id={bodyId} className="mt-1.5 text-label leading-relaxed text-muted-foreground sm:text-body">{body}</p>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
        {!intro && !outro ? <TourProgress chapters={chapters} current={chapter} /> : <span />}
        <div className="flex flex-wrap items-center justify-end gap-2">
          {intro && (
            <Button variant="ghost" onClick={onSkip}>
              Bỏ qua, mình tự khám phá
            </Button>
          )}
          {outro && (
            <Button variant="outline" onClick={() => onFinish('/dashboard')}>
              Về Tổng quan
            </Button>
          )}
          {!intro && !outro && !first && (sheet ? (
            <IconButton variant="outline" label="Quay lại" onClick={onPrev}>
              <ChevronLeft strokeWidth={1.75} aria-hidden="true" />
            </IconButton>
          ) : (
            <Button variant="ghost" leftIcon={<ChevronLeft aria-hidden="true" />} onClick={onPrev}>
              Quay lại
            </Button>
          ))}
          <Button
            data-tour-primary=""
            rightIcon={<ArrowRight aria-hidden="true" />}
            onClick={outro ? () => onFinish('/exams/new') : onNext}
          >
            {outro ? 'Tạo đề đầu tiên' : intro ? 'Bắt đầu' : 'Tiếp tục'}
          </Button>
        </div>
      </div>
    </div>
  );
}
