'use client';

import 'katex/dist/katex.min.css';
import katex from 'katex';
import { Maximize2, X } from 'lucide-react';
import { Fragment, memo, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

/**
 * Hiển thị nội dung câu hỏi / lời giải Toán theo định dạng của ngân hàng câu hỏi:
 * - `$…$` công thức trong dòng, `$$…$$` công thức riêng dòng (KaTeX).
 * - `![mô tả](media:ID)` ảnh đính kèm, tra bằng `resolveMedia`.
 * - `**chữ đậm**`, xuống dòng bằng `\n`.
 * Lỗi cú pháp LaTeX không làm vỡ trang: KaTeX hiện chuỗi gốc màu đỏ.
 */

export interface MediaInfo {
  src: string;
  alt: string;
  width: number;
  height: number;
}

export type MediaResolver = (id: string) => MediaInfo | undefined;

type Block =
  | { kind: 'text'; value: string }
  | { kind: 'display'; value: string }
  | { kind: 'image'; id: string; alt: string };

const BLOCK_RE = /\$\$([\s\S]+?)\$\$|!\[([^\]]*)\]\(media:([^)\s]+)\)/g;

function parseBlocks(source: string): Block[] {
  const blocks: Block[] = [];
  let last = 0;
  for (const m of source.matchAll(BLOCK_RE)) {
    const index = m.index ?? 0;
    if (index > last) blocks.push({ kind: 'text', value: source.slice(last, index) });
    if (m[1] !== undefined) blocks.push({ kind: 'display', value: m[1].trim() });
    else blocks.push({ kind: 'image', id: m[3], alt: m[2].startsWith('media:') ? '' : m[2] });
    last = index + m[0].length;
  }
  if (last < source.length) blocks.push({ kind: 'text', value: source.slice(last) });
  return blocks;
}

const katexCache = new Map<string, string>();

function renderTex(tex: string, displayMode: boolean) {
  const key = `${displayMode ? 'D' : 'I'}${tex}`;
  let html = katexCache.get(key);
  if (html === undefined) {
    html = katex.renderToString(tex, { displayMode, throwOnError: false, strict: 'ignore', trust: false, output: 'htmlAndMathml' });
    if (katexCache.size > 2000) katexCache.clear();
    katexCache.set(key, html);
  }
  return html;
}

const INLINE_RE = /\$([^$\n]+?)\$|\*\*([^*\n]+?)\*\*/g;

function InlineLine({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(INLINE_RE)) {
    const index = m.index ?? 0;
    if (index > last) parts.push(text.slice(last, index));
    if (m[1] !== undefined) {
      parts.push(<span key={i++} className="math-inline" dangerouslySetInnerHTML={{ __html: renderTex(m[1], false) }} />);
    } else {
      parts.push(
        <strong key={i++} className="font-semibold text-foreground">
          {m[2]}
        </strong>,
      );
    }
    last = index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

interface MathContentProps {
  source: string;
  resolveMedia?: MediaResolver;
  /** `inline`: không bọc đoạn, dùng cho lựa chọn A/B/C/D ngắn. */
  inline?: boolean;
  /** Bản in (đề A4): ảnh là `<img>` tĩnh, không có nút phóng to. */
  printable?: boolean;
  className?: string;
}

export const MathContent = memo(function MathContent({ source, resolveMedia, inline, printable, className }: MathContentProps) {
  const blocks = useMemo(() => parseBlocks(source), [source]);

  if (inline) {
    return (
      <span className={cn('math-content', className)}>
        {blocks.map((b, i) =>
          b.kind === 'text' ? (
            <InlineLine key={i} text={b.value} />
          ) : b.kind === 'display' ? (
            <span key={i} className="math-inline" dangerouslySetInnerHTML={{ __html: renderTex(b.value, false) }} />
          ) : (
            <MathImage key={i} media={resolveMedia?.(b.id)} alt={b.alt} compact printable={printable} />
          ),
        )}
      </span>
    );
  }

  return (
    <div className={cn('math-content grid gap-2.5 text-body-lg text-foreground', className)}>
      {blocks.map((b, i) => {
        if (b.kind === 'display') {
          return (
            <div
              key={i}
              className="math-display -mx-1 overflow-x-auto overflow-y-hidden px-1 py-1"
              dangerouslySetInnerHTML={{ __html: renderTex(b.value, true) }}
            />
          );
        }
        if (b.kind === 'image') return <MathImage key={i} media={resolveMedia?.(b.id)} alt={b.alt} printable={printable} />;
        const lines = b.value.split('\n').filter((line) => line.trim() !== '');
        return (
          <Fragment key={i}>
            {lines.map((line, j) => (
              <p key={j} className="leading-relaxed text-pretty">
                <InlineLine text={line.trim()} />
              </p>
            ))}
          </Fragment>
        );
      })}
    </div>
  );
});

/* ---------------- Ảnh trong câu hỏi ---------------- */

function MathImage({ media, alt, compact, printable }: { media?: MediaInfo; alt: string; compact?: boolean; printable?: boolean }) {
  const [open, setOpen] = useState(false);

  if (!media) {
    return (
      <span className="inline-flex items-center gap-2 rounded-xl border border-dashed border-border bg-surface px-3 py-2 text-caption text-muted-foreground">
        Không tải được hình minh hoạ
      </span>
    );
  }

  const label = alt || media.alt;

  if (printable) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- ảnh in giữ đúng kích thước gốc
      <img
        src={media.src}
        alt={label}
        width={media.width}
        height={media.height}
        className={cn('block h-auto max-w-full', compact ? 'max-h-32' : 'mx-auto max-h-56')}
        style={{ width: Math.min(media.width, compact ? 200 : 300) }}
      />
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          'group/img relative block w-fit max-w-full cursor-zoom-in overflow-hidden rounded-2xl border border-border bg-background p-2 transition-[box-shadow,border-color] hover:border-primary/40 hover:shadow-soft',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
          compact ? 'my-1' : 'mx-auto my-1',
        )}
        aria-label={`Phóng to hình: ${label}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- ảnh do ngân hàng câu hỏi cấp, kích thước tuỳ câu */}
        <img
          src={media.src}
          alt={label}
          width={media.width}
          height={media.height}
          loading="lazy"
          className={cn('h-auto max-w-full', compact ? 'max-h-40' : 'max-h-72 sm:max-h-80')}
          style={{ width: media.width }}
        />
        <span className="absolute right-3 bottom-3 inline-flex items-center gap-1 rounded-lg bg-foreground/75 px-2 py-1 text-[0.6875rem] font-semibold text-background transition-opacity sm:opacity-0 sm:group-hover/img:opacity-100 sm:group-focus-visible/img:opacity-100">
          <Maximize2 className="size-3.5" aria-hidden="true" /> Phóng to
        </span>
      </button>
      {open && <Lightbox media={media} alt={label} onClose={() => setOpen(false)} />}
    </>
  );
}

/** Ảnh phóng to giữa màn hình trên nền tối; bấm nền, nút X hoặc Esc để đóng. */
function Lightbox({ media, alt, onClose }: { media: MediaInfo; alt: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);

  // Không gọi close() khi dọn effect: StrictMode chạy effect hai lần, sự kiện close sẽ đóng popup ngay.
  // Gỡ <dialog> khỏi DOM là đủ để thoát chế độ modal.
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      aria-label={alt}
      className="lightbox m-0 h-dvh open:grid max-h-none w-screen max-w-none place-items-center bg-transparent p-4 backdrop:bg-[rgb(3_12_28/0.82)] backdrop:backdrop-blur-sm sm:p-10"
    >
      <button
        type="button"
        onClick={onClose}
        aria-label="Đóng ảnh"
        autoFocus
        className="fixed top-4 right-4 z-10 flex size-11 items-center justify-center rounded-full bg-white/12 text-white transition-colors hover:bg-white/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      >
        <X className="size-6" aria-hidden="true" />
      </button>
      <figure className="lightbox-figure grid max-h-full justify-items-center gap-3" onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="rounded-2xl bg-white p-3 shadow-[0_30px_80px_rgb(0_0_0/0.45)] sm:p-5">
          {/* eslint-disable-next-line @next/next/no-img-element -- ảnh phóng to giữ đúng tỉ lệ gốc */}
          <img
            src={media.src}
            alt={alt}
            className="block h-auto max-h-[calc(100dvh-10rem)] w-auto object-contain"
            style={{ width: `min(${media.width * 2}px, calc(100vw - 4rem))` }}
          />
        </div>
        <figcaption className="max-w-xl text-center text-label text-white/85">{alt}</figcaption>
      </figure>
    </dialog>
  );
}
