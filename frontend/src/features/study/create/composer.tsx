'use client';

import { ArrowUp, BookMarked, ImagePlus, Table2, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useRef, useState, type ClipboardEvent, type FormEvent, type KeyboardEvent } from 'react';
import { useToast } from '@/components/ui/toast';
import { cn } from '@/lib/cn';
import type { ImagePurpose } from '../exam-chat-api';

/** Hai cách dùng ảnh: ma trận đề để soạn đề, hoặc bài/dạng muốn ôn để agent gợi ý chương. Agent không giải bài trong ảnh. */
export const IMAGE_PURPOSES: Array<{ value: ImagePurpose; label: string; hint: string; icon: typeof Table2; defaultText: string }> = [
  { value: 'matrix', label: 'Ma trận đề', hint: 'Ảnh bảng cấu trúc đề: chương, số câu, mức độ', icon: Table2, defaultText: 'Soạn đề theo ma trận trong ảnh mình gửi' },
  { value: 'topic', label: 'Bài muốn ôn', hint: 'Ảnh bài/dạng bài: agent gợi ý chương cần ôn, không giải bài', icon: BookMarked, defaultText: 'Gợi ý chương mình cần ôn từ ảnh này' },
];

export interface Attachment {
  id: string;
  file: File;
  url: string;
}

const MAX_FILES = 4;
const MAX_BYTES = 5 * 1024 * 1024;
export const EXAM_CHAT_IMAGES = { mime: ['image/png', 'image/jpeg', 'image/webp'], totalBytes: 4 * 1024 * 1024 };
type ImageLimits = typeof EXAM_CHAT_IMAGES;

interface Props {
  disabled: boolean;
  onSend: (text: string, attachments: Attachment[]) => void;
  attachments: Attachment[];
  setAttachments: (updater: (prev: Attachment[]) => Attachment[]) => void;
  placeholder?: string;
  imageLimits?: ImageLimits;
  maxLength?: number;
  /** Mục đích ảnh đang chọn (null = để agent tự nhận diện). Có `onPurposeChange` thì hiện nút chọn khi có ảnh. */
  purpose?: ImagePurpose | null;
  onPurposeChange?: (purpose: ImagePurpose | null) => void;
}

/**
 * Ô soạn tin: tự cao theo nội dung, Enter gửi, Shift+Enter xuống dòng.
 * Ảnh: bấm nút, dán (Ctrl+V) hoặc kéo thả vào khung chat. Tối đa 4 ảnh, mỗi ảnh ≤ 5 MB.
 */
export function Composer({ disabled, onSend, attachments, setAttachments, placeholder, imageLimits, maxLength, purpose, onPurposeChange }: Props) {
  const [text, setText] = useState('');
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  const addFiles = (files: File[]) => addImages(files, attachments, setAttachments, toast, imageLimits);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (disabled || (!text.trim() && !attachments.length)) return;
    onSend(text.trim(), attachments);
    setText('');
    areaRef.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = [...e.clipboardData.files].filter((f) => f.type.startsWith('image/'));
    if (files.length) {
      e.preventDefault();
      addFiles(files);
    }
  };

  const canSend = !disabled && (text.trim().length > 0 || attachments.length > 0);

  return (
    <form onSubmit={submit} data-tour="chat-composer" className="rounded-3xl border border-border bg-background p-2 shadow-soft transition-shadow focus-within:border-primary/40 focus-within:shadow-lift">
      <AnimatePresence initial={false}>
        {attachments.length > 0 && (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="flex gap-2 overflow-x-auto px-1 pt-1 pb-2"
            aria-label="Ảnh đính kèm"
          >
            <AnimatePresence initial={false}>
              {attachments.map((a) => (
                <motion.li key={a.id} layout initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.6, opacity: 0 }} className="relative shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element -- ảnh xem trước từ máy người dùng (blob URL) */}
                  <img src={a.url} alt={a.file.name} className="size-16 rounded-2xl border border-border object-cover" />
                  <button
                    type="button"
                    onClick={() => {
                      URL.revokeObjectURL(a.url);
                      setAttachments((prev) => prev.filter((x) => x.id !== a.id));
                    }}
                    aria-label={`Bỏ ảnh ${a.file.name}`}
                    className="absolute -top-1.5 -right-1.5 flex size-6 items-center justify-center rounded-full bg-foreground text-background shadow-soft focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                  </button>
                </motion.li>
              ))}
            </AnimatePresence>
          </motion.ul>
        )}
      </AnimatePresence>

      <AnimatePresence initial={false}>
        {attachments.length > 0 && onPurposeChange && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div role="group" aria-label="Ảnh này dùng để làm gì" className="flex flex-wrap items-center gap-1.5 px-1 pb-2">
              <span className="text-caption text-muted-foreground">Ảnh này là:</span>
              {IMAGE_PURPOSES.map((p) => {
                const on = purpose === p.value;
                return (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => onPurposeChange(on ? null : p.value)}
                    aria-pressed={on}
                    title={p.hint}
                    className={cn(
                      'flex items-center gap-1.5 rounded-full border px-3 py-1 text-caption font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                      on ? 'border-primary bg-primary-subtle text-primary' : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground',
                    )}
                  >
                    <p.icon className="size-3.5" aria-hidden="true" />
                    {p.label}
                  </button>
                );
              })}
              {!purpose && <span className="text-[0.6875rem] text-muted-foreground">Không chọn thì Examind tự nhận diện.</span>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-end gap-1.5">
        <input
          ref={fileRef}
          type="file"
          accept={imageLimits?.mime.join(',') ?? 'image/*'}
          multiple
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(e) => {
            addFiles([...(e.target.files ?? [])]);
            e.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={disabled || attachments.length >= MAX_FILES}
          aria-label="Đính kèm ảnh (tối đa 4 ảnh)"
          title="Đính kèm ảnh"
          className="flex size-11 shrink-0 items-center justify-center rounded-2xl text-muted-foreground transition-colors hover:bg-surface hover:text-primary focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ImagePlus className="size-5" aria-hidden="true" />
        </button>
        <label htmlFor="chat-input" className="sr-only">
          Tin nhắn cho Examind
        </label>
        <textarea
          id="chat-input"
          ref={areaRef}
          rows={1}
          maxLength={maxLength}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          placeholder={placeholder ?? 'Nhắn Examind bạn muốn ôn gì…'}
          aria-describedby="chat-hint"
          className="max-h-44 min-h-11 flex-1 resize-none bg-transparent px-1 py-2.5 text-body text-foreground outline-none placeholder:text-muted-foreground"
        />
        <motion.button
          type="submit"
          disabled={!canSend}
          aria-label="Gửi tin nhắn"
          whileTap={canSend ? { scale: 0.9 } : undefined}
          className={cn(
            'flex size-11 shrink-0 items-center justify-center rounded-2xl transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
            canSend ? 'bg-primary text-primary-foreground hover:bg-primary-hover' : 'bg-surface-muted text-muted-foreground',
          )}
        >
          <ArrowUp className="size-5" aria-hidden="true" />
        </motion.button>
      </div>
      <p id="chat-hint" className="hidden px-3 pt-1 pb-0.5 text-[0.6875rem] text-muted-foreground sm:block">
        Enter để gửi · Shift + Enter xuống dòng · Dán hoặc kéo thả ảnh ma trận đề / bài muốn ôn (Examind không giải bài){imageLimits && ' · PNG, JPG, WebP · tổng tối đa 4 MB'}
      </p>
    </form>
  );
}

export function addImages(
  files: File[],
  current: Attachment[],
  setAttachments: Props['setAttachments'],
  toast: ReturnType<typeof useToast>,
  limits?: ImageLimits,
) {
  const images = files.filter((f) => limits ? limits.mime.includes(f.type) : f.type.startsWith('image/'));
  if (images.length < files.length) toast({ tone: 'warning', title: 'Chỉ nhận file ảnh', description: 'PNG, JPG, WebP… Các file khác đã bị bỏ qua.' });
  const maxBytes = limits?.totalBytes ?? MAX_BYTES;
  let remaining = limits ? maxBytes - current.reduce((total, item) => total + item.file.size, 0) : maxBytes;
  const ok: File[] = [];
  for (const file of images) {
    if (file.size > remaining) continue;
    ok.push(file);
    if (limits) remaining -= file.size;
  }
  if (ok.length < images.length) toast({
    tone: 'warning', title: 'Ảnh vượt dung lượng',
    description: limits ? 'Tổng ảnh trong một tin tối đa 4 MB.' : 'Mỗi ảnh tối đa 5 MB.',
  });
  const room = MAX_FILES - current.length;
  if (ok.length > room) toast({ tone: 'info', title: `Tối đa ${MAX_FILES} ảnh mỗi tin nhắn` });
  const added = ok.slice(0, Math.max(0, room)).map((file) => ({
    id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
    file,
    url: URL.createObjectURL(file),
  }));
  if (added.length) setAttachments((prev) => [...prev, ...added]);
}
