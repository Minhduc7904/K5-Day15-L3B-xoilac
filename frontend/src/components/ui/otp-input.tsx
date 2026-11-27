'use client';

import { motion, useAnimationControls } from 'motion/react';
import { useEffect, useRef, type ClipboardEvent, type KeyboardEvent } from 'react';
import { cn } from '@/lib/cn';

interface OtpInputProps {
  /** Chuỗi chữ số đã nhập; ô trống là dấu cách. */
  value: string;
  onChange: (value: string) => void;
  /** Gọi khi đủ chữ số. */
  onComplete?: (code: string) => void;
  length?: number;
  /** Nhãn của cả nhóm ô cho trình đọc màn hình. */
  label: string;
  invalid?: boolean;
  disabled?: boolean;
  autoFocus?: boolean;
  /** Đổi giá trị này để rung các ô (vd sau khi nhập sai). */
  shakeKey?: number;
  'aria-describedby'?: string;
  id?: string;
}

/**
 * Ô nhập mã OTP: tự chuyển ô, dán cả mã, Backspace lùi ô, phím mũi tên,
 * `autocomplete="one-time-code"` để điện thoại tự điền mã từ SMS/email.
 */
export function OtpInput({
  value,
  onChange,
  onComplete,
  length = 6,
  label,
  invalid,
  disabled,
  autoFocus,
  shakeKey = 0,
  id,
  ...aria
}: OtpInputProps) {
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const controls = useAnimationControls();
  const chars = Array.from({ length }, (_, i) => (value[i] && value[i] !== ' ' ? value[i] : ''));

  useEffect(() => {
    if (autoFocus) refs.current[0]?.focus();
  }, [autoFocus]);

  useEffect(() => {
    if (!shakeKey) return;
    void controls.start({ x: [0, -10, 10, -6, 6, 0], transition: { duration: 0.4 } });
    // Sau khi báo lỗi, đưa focus về ô trống đầu tiên để nhập lại ngay.
    const firstEmpty = refs.current.find((el) => el && !el.value) ?? refs.current[0];
    firstEmpty?.focus();
  }, [shakeKey, controls]);

  const emit = (next: string[]) => {
    const joined = next.map((c) => c || ' ').join('').trimEnd();
    onChange(joined);
    const code = next.join('');
    if (code.length === length && /^\d+$/.test(code)) onComplete?.(code);
  };

  const fillFrom = (start: number, digits: string) => {
    const next = [...chars];
    let i = start;
    for (const d of digits) {
      if (i >= length) break;
      next[i++] = d;
    }
    emit(next);
    refs.current[Math.min(i, length - 1)]?.focus();
  };

  const onInput = (index: number, raw: string) => {
    const digits = raw.replace(/\D/g, '');
    if (!digits) {
      const next = [...chars];
      next[index] = '';
      emit(next);
      return;
    }
    // Ô đang có số mà gõ thêm: lấy số vừa gõ (ký tự cuối).
    fillFrom(index, digits.length > 1 && chars[index] ? digits.slice(-1) : digits);
  };

  const onKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && !chars[index] && index > 0) {
      event.preventDefault();
      const next = [...chars];
      next[index - 1] = '';
      emit(next);
      refs.current[index - 1]?.focus();
    } else if (event.key === 'ArrowLeft' && index > 0) {
      event.preventDefault();
      refs.current[index - 1]?.focus();
    } else if (event.key === 'ArrowRight' && index < length - 1) {
      event.preventDefault();
      refs.current[index + 1]?.focus();
    }
  };

  const onPaste = (index: number, event: ClipboardEvent<HTMLInputElement>) => {
    const digits = event.clipboardData.getData('text').replace(/\D/g, '');
    if (!digits) return;
    event.preventDefault();
    fillFrom(index, digits);
  };

  return (
    <motion.div
      id={id}
      role="group"
      aria-label={label}
      aria-describedby={aria['aria-describedby']}
      animate={controls}
      className="flex justify-between gap-2 sm:gap-3"
    >
      {chars.map((char, i) => (
        <motion.input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          data-autofocus={autoFocus && i === 0 ? true : undefined}
          aria-label={`Chữ số ${i + 1} trên ${length}`}
          aria-invalid={invalid || undefined}
          disabled={disabled}
          value={char}
          onChange={(e) => onInput(i, e.target.value)}
          onKeyDown={(e) => onKeyDown(i, e)}
          onPaste={(e) => onPaste(i, e)}
          onFocus={(e) => e.target.select()}
          animate={char ? { scale: [1, 1.08, 1] } : { scale: 1 }}
          transition={{ duration: 0.18 }}
          className={cn(
            'h-14 w-full min-w-0 rounded-2xl border-2 bg-background text-center text-h2 font-bold text-foreground tabular-nums caret-ring',
            'transition-[border-color,background-color,box-shadow] duration-150 outline-none focus-visible:ring-4',
            'disabled:cursor-not-allowed disabled:opacity-60 sm:h-16',
            invalid
              ? 'border-danger bg-danger-subtle/40 focus-visible:ring-danger/15'
              : char
                ? 'border-primary bg-primary-subtle/60 focus-visible:border-ring focus-visible:ring-ring/20'
                : 'border-input hover:border-primary/60 focus-visible:border-ring focus-visible:ring-ring/20',
          )}
        />
      ))}
    </motion.div>
  );
}
