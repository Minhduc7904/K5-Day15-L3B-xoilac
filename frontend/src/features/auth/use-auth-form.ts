'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';

type Values = Record<string, string | boolean>;
export type FieldErrors<T extends Values> = Partial<Record<keyof T, string>>;

/**
 * State form tối giản cho các trang auth.
 * - Chỉ báo lỗi sau lần bấm gửi đầu tiên, sau đó kiểm lại mỗi lần sửa.
 * - Khi có lỗi, đưa focus vào trường lỗi đầu tiên (theo thứ tự trong DOM).
 */
export function useAuthForm<T extends Values>(initial: T, validate: (values: T) => FieldErrors<T>) {
  const [values, setValues] = useState<T>(initial);
  const [errors, setErrors] = useState<FieldErrors<T>>({});
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [focusTick, setFocusTick] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (!focusTick) return;
    formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
  }, [focusTick]);

  /** Gán nhiều trường cùng lúc. */
  const patch = (partial: Partial<T>) => {
    const next = { ...values, ...partial };
    setValues(next);
    if (submitted) setErrors(validate(next));
  };

  const setField = <K extends keyof T>(name: K, value: T[K]) => patch({ [name]: value } as unknown as Partial<T>);

  /** Nhận sự kiện submit của form, hoặc được gọi lại từ nút "Thử lại". */
  const handleSubmit = (onValid: (values: T) => Promise<void>) => async (event?: Pick<FormEvent, 'preventDefault'>) => {
    event?.preventDefault();
    if (submitting) return;
    setSubmitted(true);
    const found = validate(values);
    setErrors(found);
    if (Object.values(found).some(Boolean)) {
      setFocusTick((t) => t + 1);
      return;
    }
    setSubmitting(true);
    try {
      await onValid(values);
    } finally {
      setSubmitting(false);
    }
  };

  /** Gắn lỗi trả về từ server vào từng trường rồi focus trường đầu tiên. */
  const setServerErrors = (found: FieldErrors<T>) => {
    setErrors(found);
    setFocusTick((t) => t + 1);
  };

  return { values, errors, setField, patch, handleSubmit, submitting, formRef, setServerErrors };
}
