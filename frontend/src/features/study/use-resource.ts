'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type Resource<T> =
  | { status: 'loading'; data?: undefined; error?: undefined }
  | { status: 'error'; data?: undefined; error: Error }
  | { status: 'ready'; data: T; error?: undefined };

/** Tải dữ liệu một lần khi `key` đổi, kèm `reload()` cho nút "Thử lại". Bỏ kết quả của lần gọi cũ. */
export function useResource<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<Resource<T>>({ status: 'loading' });
  const [nonce, setNonce] = useState(0);
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    let alive = true;
    setState({ status: 'loading' });
    loadRef.current().then(
      (data) => alive && setState({ status: 'ready', data }),
      (error: unknown) => alive && setState({ status: 'error', error: error instanceof Error ? error : new Error(String(error)) }),
    );
    return () => {
      alive = false;
    };
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload } as Resource<T> & { reload: () => void };
}
