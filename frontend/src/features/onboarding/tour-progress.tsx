import { cn } from '@/lib/cn';
import type { TourChapterId } from './steps';

interface TourProgressProps {
  chapters: ReadonlyArray<{ id: string; label: string }>;
  current: TourChapterId;
}

/** Ba đoạn ngắn cho ba chặng của tour. Đoạn hiện tại dài hơn, đoạn đã qua đậm hơn đoạn chưa tới. */
export function TourProgress({ chapters, current }: TourProgressProps) {
  const at = chapters.findIndex((c) => c.id === current);
  if (at < 0) return null;
  return (
    <div role="img" aria-label={`Chặng ${at + 1} trên ${chapters.length}: ${chapters[at].label}`} className="flex items-center gap-1.5">
      {chapters.map((chapter, i) => (
        <span
          key={chapter.id}
          aria-hidden="true"
          className={cn(
            'h-1.5 rounded-full transition-[width,background-color] duration-300',
            i === at ? 'w-7 bg-primary' : i < at ? 'w-3 bg-primary/45' : 'w-3 bg-border',
          )}
        />
      ))}
    </div>
  );
}
